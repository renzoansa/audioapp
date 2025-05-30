from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import ffmpeg
import io
import tempfile
import os
import time
import mimetypes

# Supported audio formats and their corresponding ffmpeg format names
SUPPORTED_FORMATS = {
    'mp3': 'mp3',
    'wav': 'wav',
    'm4a': 'm4a',
    'ogg': 'ogg',
    'flac': 'flac',
    'aac': 'aac'
}

# Maximum allowed duration in seconds (1.5 minutes)
MAX_DURATION = 900000

@csrf_exempt
def trim_audio(request):
    if request.method == 'POST':
        start_request_time = time.time()
        print("\n=== Starting trim_audio request ===")
        try:
            # Get the audio file from the request
            audio_file = request.FILES.get('audio')
            print(f"Received audio file: {audio_file.name if audio_file else 'None'}")
            
            if not audio_file:
                print("Error: No audio file provided")
                return JsonResponse({'error': 'No audio file provided'}, status=400)

            # Get file extension and validate format
            file_ext = audio_file.name.split('.')[-1].lower()
            print(f"File extension: {file_ext}")
            
            # Check if the file extension is supported
            if file_ext not in SUPPORTED_FORMATS:
                print(f"Error: Unsupported format {file_ext}")
                return JsonResponse({
                    'error': f'Unsupported audio format. Supported formats are: {", ".join(SUPPORTED_FORMATS.keys())}'
                }, status=400)

            # Get time parameters in milliseconds and convert to seconds
            start_time_ms = float(request.POST.get('start_time', 0))
            end_time_ms = float(request.POST.get('end_time', 0))
            print(f"Time parameters - Start: {start_time_ms}ms, End: {end_time_ms}ms")
            
            # Convert milliseconds to seconds
            start_time = start_time_ms / 1000
            end_time = end_time_ms / 1000
            print(f"Converted time parameters - Start: {start_time}s, End: {end_time}s")

            # Validate time parameters
            if start_time < 0 or end_time <= start_time:
                print(f"Error: Invalid time parameters - Start: {start_time}s, End: {end_time}s")
                return JsonResponse({'error': 'Invalid time parameters'}, status=400)

            # Read the audio file into memory
            audio_bytes = audio_file.read()
            print(f"Audio file size: {len(audio_bytes)} bytes")
            
            # Create output stream
            output_stream = io.BytesIO()

            try:
                # Create a temporary file for input
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as temp_input:
                    temp_input.write(audio_bytes)
                    temp_input.flush()
                    print(f"Created temporary input file: {temp_input.name}")
                    
                    try:
                        # Get audio duration using ffprobe
                        probe = ffmpeg.probe(temp_input.name)
                        duration = float(probe['format']['duration'])
                        print(f"Original audio duration: {duration} seconds")
                    except ffmpeg.Error as e:
                        print(f"Error probing file: {str(e)}")
                        return JsonResponse({
                            'error': 'Invalid audio file format or corrupted file'
                        }, status=400)
                    
                    # Validate audio duration
                    if duration > MAX_DURATION:
                        print(f"Error: Audio duration {duration}s exceeds maximum {MAX_DURATION}s")
                        return JsonResponse({
                            'error': f'Audio file is too long. Maximum duration is {MAX_DURATION} seconds'
                        }, status=400)
                    
                    # Validate end_time against actual duration
                    if end_time > duration:
                        print(f"Adjusting end_time from {end_time}s to {duration}s")
                        end_time = duration

                    # Create a temporary file for output
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_output:
                        print(f"Created temporary output file: {temp_output.name}")
                        try:
                            # Use ffmpeg to trim and convert the audio
                            stream = ffmpeg.input(temp_input.name)
                            stream = ffmpeg.output(stream, temp_output.name,
                                                 ss=start_time,
                                                 t=end_time-start_time,
                                                 acodec='libmp3lame',
                                                 vn=None)  # Disable video stream
                            
                            print("Running ffmpeg command...")
                            # Run the ffmpeg command
                            ffmpeg.run(stream, overwrite_output=True)
                            
                            # Read the output file
                            temp_output.seek(0)
                            output_stream.write(temp_output.read())
                            output_stream.seek(0)
                            print(f"Output file size: {output_stream.getbuffer().nbytes} bytes")
                        except ffmpeg.Error as e:
                            print(f"FFmpeg error: {str(e)}")
                            return JsonResponse({
                                'error': 'Error processing audio file',
                                'details': str(e)
                            }, status=500)

                # Clean up temporary files
                os.unlink(temp_input.name)
                os.unlink(temp_output.name)
                print("Cleaned up temporary files")

                # Verify the output is not empty
                if output_stream.getbuffer().nbytes == 0:
                    print("Error: Generated audio file is empty")
                    return JsonResponse({'error': 'Generated audio file is empty'}, status=500)

                # Calculate and print request duration
                request_duration = time.time() - start_request_time
                print(f"Request completed successfully in {request_duration:.2f} seconds")

                # Return the trimmed audio file
                response = FileResponse(output_stream)
                response['Content-Type'] = 'audio/mpeg'
                response['Content-Disposition'] = f'attachment; filename="trimmed_{audio_file.name}"'
                print("=== Request completed successfully ===\n")
                return response

            except Exception as e:
                print(f"Error processing file: {str(e)}")
                return JsonResponse({
                    'error': 'Error processing audio file',
                    'details': str(e)
                }, status=500)

        except Exception as e:
            print(f"Unexpected error: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    print("Error: Method not allowed")
    return JsonResponse({'error': 'Method not allowed'}, status=405)