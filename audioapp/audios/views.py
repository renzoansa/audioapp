from django.http import FileResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import ffmpeg
import io
import tempfile
import os
import time

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
        try:
            # Get the audio file from the request
            audio_file = request.FILES.get('audio')
            
            # Get time parameters in milliseconds and convert to seconds
            start_time_ms = float(request.POST.get('start_time', 0))
            end_time_ms = float(request.POST.get('end_time', 0))
            
            # Convert milliseconds to seconds
            start_time = start_time_ms / 1000
            end_time = end_time_ms / 1000

            if not audio_file:
                return JsonResponse({'error': 'No audio file provided'}, status=400)

            # Validate time parameters
            if start_time < 0 or end_time <= start_time:
                return JsonResponse({'error': 'Invalid time parameters'}, status=400)

            # Get file extension and validate format
            file_ext = audio_file.name.split('.')[-1].lower()
            if file_ext not in SUPPORTED_FORMATS:
                return JsonResponse({
                    'error': f'Unsupported audio format. Supported formats are: {", ".join(SUPPORTED_FORMATS.keys())}'
                }, status=400)

            # Read the audio file into memory
            audio_bytes = audio_file.read()
            
            # Create output stream
            output_stream = io.BytesIO()

            try:
                # Create a temporary file for input
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_ext}') as temp_input:
                    temp_input.write(audio_bytes)
                    temp_input.flush()
                    
                    # Get audio duration using ffprobe
                    probe = ffmpeg.probe(temp_input.name)
                    duration = float(probe['format']['duration'])
                    
                    # Validate audio duration
                    if duration > MAX_DURATION:
                        return JsonResponse({
                            'error': f'Audio file is too long. Maximum duration is {MAX_DURATION} seconds'
                        }, status=400)
                    
                    # Validate end_time against actual duration
                    if end_time > duration:
                        end_time = duration

                    # Create a temporary file for output
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_output:
                        # Use ffmpeg to trim and convert the audio
                        stream = ffmpeg.input(temp_input.name, format=SUPPORTED_FORMATS[file_ext])
                        stream = ffmpeg.output(stream, temp_output.name,
                                             ss=start_time,
                                             t=end_time-start_time,
                                             acodec='libmp3lame',
                                             vn=None)  # Disable video stream
                        
                        # Run the ffmpeg command
                        ffmpeg.run(stream, overwrite_output=True)
                        
                        # Read the output file
                        temp_output.seek(0)
                        output_stream.write(temp_output.read())
                        output_stream.seek(0)

                # Clean up temporary files
                os.unlink(temp_input.name)
                os.unlink(temp_output.name)

                # Verify the output is not empty
                if output_stream.getbuffer().nbytes == 0:
                    return JsonResponse({'error': 'Generated audio file is empty'}, status=500)

                # Calculate and print request duration
                request_duration = time.time() - start_request_time
                print(f"Request duration: {request_duration:.2f} seconds")

                # Return the trimmed audio file
                response = FileResponse(output_stream)
                response['Content-Type'] = 'audio/mpeg'
                response['Content-Disposition'] = f'attachment; filename="trimmed_{audio_file.name}"'

                return response

            except ffmpeg.Error as ffmpeg_err:
                return JsonResponse({
                    'error': 'ffmpeg error',
                    'stderr': ffmpeg_err.stderr.decode('utf-8') if ffmpeg_err.stderr else 'No stderr output'
                }, status=500)

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Method not allowed'}, status=405)