from pathlib import Path
from PyPDF2 import PdfReader
from mutagen.mp3 import MP3
from moviepy import ImageSequenceClip, AudioFileClip
from playwright.sync_api import sync_playwright
import tempfile
import requests
from gtts import gTTS

# Replace with your Together.ai API key
TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"
TOGETHER_API_KEY = "b8a9fc8e237d88e735ebdf510720730ff6bb592dd211f85a7416bc38563cd857"

# Output directory for presentations and videos
output_dir = Path("C:/TTS")
output_dir.mkdir(parents=True, exist_ok=True)


def process_file(file):
    try:
        if not file:
            print("No file uploaded. Proceeding with only the question...")
            return None

        file_path = Path(file.name)
        if file_path.suffix == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        elif file_path.suffix == '.pdf':
            reader = PdfReader(file_path)
            return "\n".join([page.extract_text() for page in reader.pages])
        else:
            return "Unsupported file format. Please upload a .txt or .pdf file."
    except Exception as e:
        return f"Error processing file: {e}"


def generate_ta_response(content, question):
    """
    Generate a response in a teaching assistant style using Together.ai.
    """
    try:
        combined_content = question if not content else f"{content}\n\nUser's Question: {question}"
        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",  # Replace with your preferred model
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a friendly and engaging Teaching Assistant. Respond in a conversational tone, making the "
                        "explanation easy to follow. Break down concepts step-by-step, use examples, and incorporate "
                        "questions related to the topic to keep the user engaged."
                    ),
                },
                {"role": "user", "content": combined_content},
            ],
            "max_tokens": 1000,
            "temperature": 0.7,
        }
        response = requests.post(TOGETHER_API_URL, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error generating TA response: {e}"


def save_tts_audio(ta_script):
    """
    Generate TTS audio for the TA script and save it.
    """
    try:
        print("Generating TTS audio...")
        speech_file_path = output_dir / "ta_explanation_audio.mp3"
        tts = gTTS(text=ta_script, lang='en')
        tts.save(str(speech_file_path))
        return speech_file_path
    except Exception as e:
        return f"Error generating TTS audio: {e}"


def generate_reveal_js_presentation(ta_script):
    """
    Generate a Reveal.js HTML presentation using Together.ai.
    """
    try:
        headers = {
            "Authorization": f"Bearer {TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",  # Replace with your preferred model
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a creative and detail-oriented presentation designer skilled in Reveal.js. Generate a "
                        "clean, professional, and fully functional Reveal.js HTML presentation based on the provided "
                        "content. Use the 'moon' theme for a stylish look. Divide the content into multiple slides using "
                        "`<section>` tags in Reveal.js. Each paragraph or logical block should be placed in a new "
                        "`<section>`. Use the first line of each logical block as the slide title, formatted as `<h1>` or "
                        "`<h2>`. Ensure each slide contains no more than 3-4 sentences or a single logical idea. "
                        "Automatically include all necessary script and link tags for Reveal.js and MathJax. Initialize "
                        "Reveal.js in the HTML file, ensuring the presentation is fully functional without requiring manual "
                        "modifications. Use MathJax to render LaTeX equations properly. For block equations, use `\\[ ... \\]`, "
                        "and for inline equations, use `$ ... $`. Ensure the HTML is standalone, includes all dependencies, "
                        "and is ready to open in any modern browser. Highlight code blocks using Highlight.js."
                    ),
                },
                {"role": "user", "content": ta_script},
            ],
            "max_tokens": 2000,
            "temperature": 0.7,
        }
        response = requests.post(TOGETHER_API_URL, headers=headers, json=data)
        response.raise_for_status()
        reveal_html = response.json()["choices"][0]["message"]["content"]
        presentation_path = output_dir / "presentation.html"
        with open(presentation_path, "w", encoding="utf-8") as f:
            f.write(reveal_html)
        return presentation_path
    except Exception as e:
        return f"Error generating Reveal.js presentation: {e}"


def render_slides_to_images(reveal_html_path):
    """
    Render Reveal.js slides to images using Playwright.
    """
    try:
        print("Rendering slides to images using Playwright...")
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(viewport={"width": 1920, "height": 1080})
            page = context.new_page()
            page.goto(f"file:///{reveal_html_path}")

            # Wait until the Reveal.js object is defined and initialized
            page.wait_for_function("typeof Reveal !== 'undefined' && Reveal.isReady")
            print("Reveal.js is ready.")

            slides = []
            slide_sections = page.locator(".slides > section")
            slide_count = slide_sections.count()

            if slide_count == 0:
                raise ValueError("No slides found in the Reveal.js presentation.")

            for i in range(slide_count):
                # Navigate to the slide
                page.evaluate(f"Reveal.slide({i});")
                page.wait_for_timeout(1000)  # Allow slide transition
                temp_img = tempfile.NamedTemporaryFile(suffix=".png", delete=False).name
                page.screenshot(path=temp_img, full_page=True)
                slides.append(temp_img)

            browser.close()
            return slides
    except Exception as e:
        print(f"Error rendering slides to images: {e}")
        return []


def calculate_audio_timings(ta_script, audio_file, num_slides):
    """
    Calculate timings for audio synchronization based on word count and fallback to equal distribution.
    """
    try:
        audio = MP3(audio_file)
        total_duration = audio.info.length  # Total audio duration in seconds

        # Split script into slides and count words per slide
        slides = ta_script.split("\n\n")
        if len(slides) != num_slides:
            raise ValueError("Mismatch between slide count and provided script sections.")

        word_counts = [len(slide.split()) for slide in slides]
        total_words = sum(word_counts)

        if total_words == 0 or num_slides == 0:
            raise ValueError("Invalid content or no slides available.")

        # Calculate durations proportionally to word counts
        slide_durations = [(word_count / total_words) * total_duration for word_count in word_counts]

        # Adjust last slide duration to ensure total duration matches audio
        slide_durations[-1] += total_duration - sum(slide_durations)

        # Ensure slide durations are valid and cumulative
        cumulative_timings = [0]
        for duration in slide_durations:
            cumulative_timings.append(round(cumulative_timings[-1] + duration, 2))

        return cumulative_timings[:-1]  # Start timings for each slide
    except Exception as e:
        print(f"Error calculating slide timings: {e}. Falling back to equal distribution.")
        try:
            # Fallback: Equally distribute timings across slides
            if num_slides == 0:
                raise ValueError("No slides available for fallback timing.")
            return [round(i * (total_duration / num_slides), 2) for i in range(num_slides)]
        except Exception as fallback_error:
            print(f"Fallback error: {fallback_error}")
            return []


def generate_video_output(slide_image_paths, audio_path, slide_timings):
    """
    Generate a video presentation from slides and audio with precise synchronization.
    """
    if not slide_image_paths:
        print("No slide images found. Skipping video generation.")
        return None
    try:
        print("Generating video output...")
        audio_clip = AudioFileClip(str(audio_path))

        # Ensure slide durations match the number of slides
        slide_durations = [t2 - t1 for t1, t2 in zip(slide_timings, slide_timings[1:])]
        if len(slide_durations) != len(slide_image_paths):
            difference = len(slide_image_paths) - len(slide_durations)
            if difference > 0:
                # Add equal durations for the remaining slides
                avg_duration = audio_clip.duration / len(slide_image_paths)
                slide_durations += [avg_duration] * difference
            else:
                # Trim extra durations if more durations than slides
                slide_durations = slide_durations[:len(slide_image_paths)]

        video_clip = ImageSequenceClip(slide_image_paths, durations=slide_durations)
        video_clip.audio = audio_clip

        video_path = output_dir / "presentation_video.mp4"
        video_clip.write_videofile(str(video_path), codec="libx264", audio_codec="aac")
        return video_path
    except Exception as e:
        print(f"Error generating video: {e}")
        return None


def create_presentation(file, question):
    """
    Create the full presentation workflow with enhanced synchronization.
    """
    try:
        file_content = process_file(file)
        if file_content == "Unsupported file format. Please upload a .txt or .pdf file.":
            return file_content, None

        ta_script = generate_ta_response(file_content, question)
        if "Error" in ta_script:
            return ta_script, None

        speech_file_path = save_tts_audio(ta_script)
        if "Error" in str(speech_file_path):
            return speech_file_path, None

        reveal_html_path = generate_reveal_js_presentation(ta_script)
        if "Error" in str(reveal_html_path):
            return reveal_html_path, None

        slides = render_slides_to_images(reveal_html_path)
        if not slides:
            return "Error rendering slides.", None

        # Improved synchronization logic
        slide_timings = calculate_audio_timings(ta_script, speech_file_path, len(slides))
        if not slide_timings or len(slide_timings) != len(slides):
            return "Error calculating slide timings.", None

        video_path = generate_video_output(slides, speech_file_path, slide_timings)
        if not video_path:
            return "Error generating video.", None

        return "Presentation created successfully!", str(video_path)
    except Exception as e:
        print(f"Unexpected error: {e}")
        return "An unexpected error occurred.", None