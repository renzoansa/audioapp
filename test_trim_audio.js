const axios = require('axios');
const fs = require('fs');
const path = require('path');
const { performance } = require('perf_hooks');

async function makeTrimRequest(requestId) {
    // URL of your Django server
    const url = 'http://localhost:8000/api/audios/trim/';
    
    // Path to your test audio file
    const audioFilePath = 'test_audio.m4a';
    
    // Check if the test file exists
    if (!fs.existsSync(audioFilePath)) {
        console.error(`Error: Test audio file '${audioFilePath}' not found!`);
        return null;
    }
    
    // Parameters for trimming
    const data = {
        start_time: 5.0,
        end_time: 10.0
    };
    
    try {
        // Create form data
        const formData = new FormData();
        formData.append('audio', fs.createReadStream(audioFilePath));
        formData.append('start_time', data.start_time);
        formData.append('end_time', data.end_time);
        
        // Make the POST request
        const startTime = performance.now();
        const response = await axios.post(url, formData, {
            headers: {
                ...formData.getHeaders()
            },
            responseType: 'arraybuffer'
        });
        const endTime = performance.now();
        
        // Calculate processing times
        const totalTime = (endTime - startTime) / 1000; // Convert to seconds
        const serverTime = parseFloat(response.headers['x-process-time'] || 0);
        
        // Save the trimmed audio with unique name
        const outputPath = `trimmed_output_${requestId}.mp3`;
        fs.writeFileSync(outputPath, response.data);
        
        console.log(`Request ${requestId}: Total time: ${totalTime.toFixed(2)}s, Server processing: ${serverTime.toFixed(2)}s`);
        return { totalTime, serverTime };
        
    } catch (error) {
        console.error(`Error occurred in request ${requestId}:`, error.message);
        return null;
    }
}

async function testTrimAudioConcurrent(numRequests) {
    const startTime = performance.now();
    const processingTimes = [];
    
    // Create an array of promises for concurrent requests
    const promises = Array.from({ length: numRequests }, (_, i) => makeTrimRequest(i));
    
    // Wait for all requests to complete
    const results = await Promise.all(promises);
    
    // Filter out failed requests and collect processing times
    results.forEach(result => {
        if (result) {
            processingTimes.push(result);
        }
    });
    
    const endTime = performance.now();
    const totalTime = (endTime - startTime) / 1000;
    
    // Calculate statistics
    if (processingTimes.length > 0) {
        const serverTimes = processingTimes.map(t => t.serverTime);
        const totalTimes = processingTimes.map(t => t.totalTime);
        
        const calculateStats = (arr) => ({
            average: arr.reduce((a, b) => a + b, 0) / arr.length,
            median: arr.sort((a, b) => a - b)[Math.floor(arr.length / 2)],
            min: Math.min(...arr),
            max: Math.max(...arr)
        });
        
        const serverStats = calculateStats(serverTimes);
        const totalStats = calculateStats(totalTimes);
        
        console.log("\nEstadísticas de procesamiento:");
        console.log(`Tiempo total de ejecución: ${totalTime.toFixed(2)} segundos`);
        
        console.log("\nTiempo de procesamiento del servidor:");
        console.log(`Promedio: ${serverStats.average.toFixed(2)} segundos`);
        console.log(`Mediana: ${serverStats.median.toFixed(2)} segundos`);
        console.log(`Mínimo: ${serverStats.min.toFixed(2)} segundos`);
        console.log(`Máximo: ${serverStats.max.toFixed(2)} segundos`);
        
        console.log("\nTiempo total por solicitud (incluyendo red):");
        console.log(`Promedio: ${totalStats.average.toFixed(2)} segundos`);
        console.log(`Mediana: ${totalStats.median.toFixed(2)} segundos`);
        console.log(`Mínimo: ${totalStats.min.toFixed(2)} segundos`);
        console.log(`Máximo: ${totalStats.max.toFixed(2)} segundos`);
        
        console.log(`\nTotal de solicitudes exitosas: ${processingTimes.length}/${numRequests}`);
    }
}

// Parse command line arguments
const args = process.argv.slice(2);
const numRequests = parseInt(args[0]) || 100;

if (numRequests <= 0) {
    console.error("Error: El número de requests debe ser mayor que 0");
    process.exit(1);
}

console.log(`Iniciando ${numRequests} requests concurrentes...`);
testTrimAudioConcurrent(numRequests); 