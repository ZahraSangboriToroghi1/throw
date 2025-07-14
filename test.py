import whisper
import numpy as np
import scipy.io.wavfile as wavfile
import os
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch

# بررسی sounddevice
try:
    import sounddevice as sd
    SOUNDDEVICE_AVAILABLE = True
    print("✅ sounddevice loaded successfully")
except ImportError:
    SOUNDDEVICE_AVAILABLE = False
    print("❌ sounddevice not available")

# تنظیمات اولیه
whisper_model_name = "base"  
meditron_model_path = "./model"
output_dir = "./"

print("=== Medical System Test ===")
print(f"Model path: {meditron_model_path}")
print(f"Model exists: {os.path.exists(meditron_model_path)}")

# بررسی وجود مدل
if not os.path.exists(meditron_model_path):
    print(f"❌ Error: Model folder '{meditron_model_path}' not found!")
    print("Available folders:")
    for item in os.listdir("."):
        if os.path.isdir(item):
            print(f"  📁 {item}")
    exit(1)

# بارگذاری مدل Whisper
print("\n🔄 Loading Whisper model...")
try:
    whisper_model = whisper.load_model(whisper_model_name)
    print("✅ Whisper model loaded successfully")
except Exception as e:
    print(f"❌ Error loading Whisper: {e}")
    exit(1)

# بارگذاری مدل Meditron-7B
print("🔄 Loading Meditron model...")
try:
    quant_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16
    )
    
    meditron_model = AutoModelForCausalLM.from_pretrained(
        meditron_model_path,
        quantization_config=quant_config,
        device_map="cpu",
        local_files_only=True,
        trust_remote_code=True
    )
    print("✅ Meditron model loaded successfully")
    
    meditron_tokenizer = AutoTokenizer.from_pretrained(
        meditron_model_path,
        local_files_only=True,
        trust_remote_code=True
    )
    print("✅ Meditron tokenizer loaded successfully")
    
    meditron_pipe = pipeline(
        "text-generation",
        model=meditron_model,
        tokenizer=meditron_tokenizer,
        truncation=True,
        max_new_tokens=200,
        do_sample=True,
        temperature=0.3,
        top_p=0.9,
        top_k=50
    )
    print("✅ Meditron pipeline created successfully")
    
except Exception as e:
    print(f"❌ Error loading Meditron model: {e}")
    exit(1)

# بررسی دستگاه‌های صوتی موجود
def list_audio_devices():
    """لیست کردن دستگاه‌های صوتی موجود"""
    if not SOUNDDEVICE_AVAILABLE:
        return []
    
    try:
        devices = sd.query_devices()
        print("\n🎤 Available audio devices:")
        print("-" * 50)
        input_devices = []
        
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:
                print(f"  {i}: {device['name']} (Input channels: {device['max_input_channels']})")
                input_devices.append(i)
        
        if not input_devices:
            print("  ❌ No input devices found!")
        
        return input_devices
    except Exception as e:
        print(f"❌ Error listing devices: {e}")
        return []

# تابع ضبط صدا با انتخاب دستگاه
def record_audio_with_device_selection(duration=5, sample_rate=16000, output_file="recorded_audio.wav"):
    """ضبط صدا با انتخاب دستگاه"""
    if not SOUNDDEVICE_AVAILABLE:
        print("❌ sounddevice not available. Please use option 1 (upload file).")
        return None
    
    # لیست دستگاه‌ها
    input_devices = list_audio_devices()
    
    if not input_devices:
        print("❌ No audio input devices found!")
        print("Solutions:")
        print("1. Check microphone connection")
        print("2. Update audio drivers")
        print("3. Check Windows privacy settings for microphone access")
        print("4. Use option 1 to upload an audio file instead")
        return None
    
    # انتخاب دستگاه
    try:
        if len(input_devices) == 1:
            device_id = input_devices[0]
            print(f"🎤 Using device {device_id}")
        else:
            print(f"\nSelect input device (0-{len(input_devices)-1}):")
            for i, dev_id in enumerate(input_devices):
                print(f"  {i}: Device {dev_id}")
            
            choice = int(input("Enter device number: "))
            if 0 <= choice < len(input_devices):
                device_id = input_devices[choice]
            else:
                print("❌ Invalid device selection!")
                return None
        
        print(f"🎤 Recording for {duration} seconds using device {device_id}...")
        
        # ضبط صدا
        audio = sd.rec(
            int(duration * sample_rate), 
            samplerate=sample_rate, 
            channels=1, 
            device=device_id,
            dtype=np.float32
        )
        sd.wait()
        
        # ذخیره فایل
        output_path = os.path.join(output_dir, output_file)
        wavfile.write(output_path, sample_rate, (audio * 32767).astype(np.int16))
        print(f"💾 Audio saved as {output_file}")
        
        return output_path
        
    except Exception as e:
        print(f"❌ Error recording audio: {e}")
        print("Try:")
        print("1. Close other audio applications")
        print("2. Run as administrator")
        print("3. Use option 1 to upload an audio file")
        return None

# تابع ضبط ساده (فال‌بک)
def simple_record_audio(duration=5, sample_rate=16000, output_file="recorded_audio.wav"):
    """ضبط ساده بدون انتخاب دستگاه"""
    if not SOUNDDEVICE_AVAILABLE:
        return None
    
    try:
        print(f"🎤 Recording for {duration} seconds...")
        audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
        sd.wait()
        output_path = os.path.join(output_dir, output_file)
        wavfile.write(output_path, sample_rate, audio)
        print(f"💾 Audio saved as {output_file}")
        return output_path
    except Exception as e:
        print(f"❌ Simple recording failed: {e}")
        return None

# منوی انتخاب کاربر
print("\n" + "="*50)
print("🎯 Select an option:")
print("1. Upload an audio file")
print("2. Record audio directly (with device selection)")
print("3. Record audio directly (simple method)")
print("4. Test with sample text (skip audio)")
choice = input("Enter 1, 2, 3, or 4: ").strip()

transcription = ""

if choice == "1":
    audio_path = input("Enter the audio file path: ").strip()
    # حذف گیومه‌ها اگر وجود داشته باشد
    audio_path = audio_path.strip('"').strip("'")
    
    if not os.path.exists(audio_path):
        print("❌ Error: Audio file not found!")
        print(f"Tried path: {audio_path}")
        exit(1)
    
    print(f"✅ Audio file found: {audio_path}")

elif choice == "2":
    try:
        duration = int(input("Enter recording duration (seconds, e.g., 5): "))
        audio_path = record_audio_with_device_selection(duration=duration)
        if not audio_path:
            print("❌ Recording failed!")
            exit(1)
    except ValueError:
        print("❌ Invalid duration!")
        exit(1)

elif choice == "3":
    try:
        duration = int(input("Enter recording duration (seconds, e.g., 5): "))
        audio_path = simple_record_audio(duration=duration)
        if not audio_path:
            print("❌ Recording failed!")
            exit(1)
    except ValueError:
        print("❌ Invalid duration!")
        exit(1)

elif choice == "4":
    transcription = "Patient shows signs of pneumonia in the right lower lobe. Heart size is normal. No fractures visible."
    print("📝 Using sample text:")
    print("-" * 50)
    print(transcription)
    print("-" * 50)
    audio_path = None

else:
    print("❌ Invalid choice!")
    exit(1)

# تبدیل گفتار به متن (اگر فایل صوتی دارید)
if audio_path and transcription == "":
    print("\n🔄 Transcribing audio...")
    try:
        result = whisper_model.transcribe(audio_path, language="English", fp16=False)
        transcription = result["text"]
        print("📝 Transcription:")
        print("-" * 50)
        print(transcription)
        print("-" * 50)
    except Exception as e:
        print(f"❌ Error in transcription: {e}")
        exit(1)

# تولید گزارش رادیولوژی با Meditron
print("\n🔄 Generating radiology report...")
try:
    report_prompt = f"""
SYSTEM PROMPT: You are a certified radiologist specialized in interpreting images and generating structured diagnostic reports.
Generate a professional radiology report based on the following findings and patient information.

Patient Information
Name: Not provided
Patient ID: Not provided
Gender: Not provided
Date of Birth: Not provided
Exam Date: Not provided

Imaging Modality
Modality: Not specified

Clinical Findings
{transcription}

User Instructions:
Target Language for Output: English
Desired Report Structure:
* Patient Demographics
* Examination Details
* Clinical Findings
* Measurements
* Impression
* Recommendations
Terminology Standard: CE-compliant
Formatting: Plain text
"""

    output = meditron_pipe(report_prompt, return_full_text=False)
    
    print("📋 Radiology Report:")
    print("=" * 50)
    print(output[0]["generated_text"])
    print("=" * 50)
    
except Exception as e:
    print(f"❌ Error generating report: {e}")
    exit(1)

print("\n✅ Process completed successfully!")