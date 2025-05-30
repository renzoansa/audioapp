import requests
import os
from concurrent.futures import ThreadPoolExecutor
import time
from statistics import mean, median
import argparse

def make_trim_request(request_id):
    # URL of your Django server
    url = 'http://localhost:8000/api/audios/trim/'
    
    # Path to your test audio file
    audio_file_path = 'test_audio.m4a'
    
    # Check if the test file exists
    if not os.path.exists(audio_file_path):
        print(f"Error: Test audio file '{audio_file_path}' not found!")
        return None
    
    # Parameters for trimming
    data = {
        'start_time': 5.0,
        'end_time': 10.0
    }
    
    # Open the audio file
    with open(audio_file_path, 'rb') as audio_file:
        files = {
            'audio': (os.path.basename(audio_file_path), audio_file, 'audio/mpeg')
        }
        
        try:
            # Make the POST request
            start_time = time.time()
            response = requests.post(url, data=data, files=files)
            end_time = time.time()
            
            # Calculate processing times
            total_time = end_time - start_time
            server_time = float(response.headers.get('X-Process-Time', 0))
            
            # Check if the request was successful
            if response.status_code == 200:
                # Save the trimmed audio with unique name
                output_path = f'trimmed_output_{request_id}.mp3'
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                print(f"Request {request_id}: Total time: {total_time:.2f}s, Server processing: {server_time:.2f}s")
                return {'total_time': total_time, 'server_time': server_time}
            else:
                print(f"Error in request {request_id}: {response.status_code}")
                print(response.json())
                return None
                
        except Exception as e:
            print(f"Error occurred in request {request_id}: {str(e)}")
            return None

def test_trim_audio_concurrent(num_requests):
    start_time = time.time()
    processing_times = []
    
    # Create a ThreadPoolExecutor with the same number of workers as requests
    with ThreadPoolExecutor(max_workers=num_requests) as executor:
        # Submit the specified number of requests
        futures = [executor.submit(make_trim_request, i) for i in range(num_requests)]
        
        # Wait for all requests to complete and collect results
        for future in futures:
            result = future.result()
            if result:
                processing_times.append(result)
    
    end_time = time.time()
    total_time = end_time - start_time
    
    # Calculate statistics
    if processing_times:
        server_times = [t['server_time'] for t in processing_times]
        total_times = [t['total_time'] for t in processing_times]
        
        print("\nEstadísticas de procesamiento:")
        print(f"Tiempo total de ejecución: {total_time:.2f} segundos")
        print("\nTiempo de procesamiento del servidor:")
        print(f"Promedio: {mean(server_times):.2f} segundos")
        print(f"Mediana: {median(server_times):.2f} segundos")
        print(f"Mínimo: {min(server_times):.2f} segundos")
        print(f"Máximo: {max(server_times):.2f} segundos")
        
        print("\nTiempo total por solicitud (incluyendo red):")
        print(f"Promedio: {mean(total_times):.2f} segundos")
        print(f"Mediana: {median(total_times):.2f} segundos")
        print(f"Mínimo: {min(total_times):.2f} segundos")
        print(f"Máximo: {max(total_times):.2f} segundos")
        
        print(f"\nTotal de solicitudes exitosas: {len(processing_times)}/{num_requests}")

def main():
    parser = argparse.ArgumentParser(description='Test concurrent audio trimming requests')
    parser.add_argument('-n', '--num-requests', type=int, default=100,
                      help='Número de requests concurrentes a realizar (default: 100)')
    
    args = parser.parse_args()
    
    if args.num_requests <= 0:
        print("Error: El número de requests debe ser mayor que 0")
        return
    
    print(f"Iniciando {args.num_requests} requests concurrentes...")
    test_trim_audio_concurrent(args.num_requests)

if __name__ == '__main__':
    main() 