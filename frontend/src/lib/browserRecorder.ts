export interface BrowserCallRecorder {
  stop: () => Promise<Blob>;
  cancel: () => Promise<void>;
}

function mergeChannels(inputBuffer: AudioBuffer): Float32Array {
  const channelCount = inputBuffer.numberOfChannels;
  const frameCount = inputBuffer.length;

  if (channelCount === 1) {
    return new Float32Array(inputBuffer.getChannelData(0));
  }

  const output = new Float32Array(frameCount);
  for (let channelIndex = 0; channelIndex < channelCount; channelIndex += 1) {
    const channelData = inputBuffer.getChannelData(channelIndex);
    for (let frameIndex = 0; frameIndex < frameCount; frameIndex += 1) {
      output[frameIndex] += channelData[frameIndex] / channelCount;
    }
  }

  return output;
}

function encodeWav(samples: Float32Array, sampleRate: number): Blob {
  const bytesPerSample = 2;
  const blockAlign = bytesPerSample;
  const buffer = new ArrayBuffer(44 + samples.length * bytesPerSample);
  const view = new DataView(buffer);

  const writeString = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i += 1) {
      view.setUint8(offset + i, value.charCodeAt(i));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * bytesPerSample, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, samples.length * bytesPerSample, true);

  let offset = 44;
  for (let i = 0; i < samples.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, samples[i]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    offset += bytesPerSample;
  }

  return new Blob([buffer], { type: "audio/wav" });
}

export async function startBrowserCallRecording(): Promise<BrowserCallRecorder> {
  if (typeof window === "undefined" || !navigator.mediaDevices) {
    throw new Error("Browser recording is not available in this environment.");
  }

  if (!window.isSecureContext) {
    throw new Error("Recording requires HTTPS. Access this site using https:// or http://localhost");
  }

  const displayStream = await navigator.mediaDevices.getDisplayMedia({
    video: true,
    audio: true,
  });

  if (displayStream.getAudioTracks().length === 0) {
    displayStream.getTracks().forEach((track) => track.stop());
    throw new Error("No meeting audio was shared. Choose the Meet tab and enable tab audio.");
  }

  let microphoneStream: MediaStream | null = null;

  try {
    microphoneStream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
      },
    });
  } catch {
    displayStream.getTracks().forEach((track) => track.stop());
    throw new Error("Microphone access is required to capture both sides of the call.");
  }

  const audioContext = new AudioContext();
  await audioContext.resume();

  const displaySource = audioContext.createMediaStreamSource(displayStream);
  const microphoneSource = audioContext.createMediaStreamSource(microphoneStream);
  const processor = audioContext.createScriptProcessor(4096, 2, 1);
  const silentGain = audioContext.createGain();
  silentGain.gain.value = 0;

  const chunks: Float32Array[] = [];

  displaySource.connect(processor);
  microphoneSource.connect(processor);
  processor.connect(silentGain);
  silentGain.connect(audioContext.destination);

  processor.onaudioprocess = (event) => {
    chunks.push(mergeChannels(event.inputBuffer));
  };

  const cleanup = async () => {
    processor.disconnect();
    silentGain.disconnect();
    displaySource.disconnect();
    microphoneSource.disconnect();
    displayStream.getTracks().forEach((track) => track.stop());
    microphoneStream?.getTracks().forEach((track) => track.stop());
    if (audioContext.state !== "closed") {
      await audioContext.close();
    }
  };

  return {
    stop: async () => {
      await cleanup();

      const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
      const merged = new Float32Array(totalLength);
      let offset = 0;
      for (const chunk of chunks) {
        merged.set(chunk, offset);
        offset += chunk.length;
      }

      if (merged.length === 0) {
        throw new Error("No audio was captured. Make sure Meet tab audio is shared.");
      }

      return encodeWav(merged, audioContext.sampleRate);
    },
    cancel: async () => {
      await cleanup();
    },
  };
}
