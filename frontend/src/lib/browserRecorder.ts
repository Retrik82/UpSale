export interface BrowserCallRecorder {
  stop: () => Promise<Blob>;
  cancel: () => Promise<void>;
}

function captureChannels(inputBuffer: AudioBuffer): Float32Array[] {
  const frameCount = inputBuffer.length;
  const displayChannel = new Float32Array(frameCount);
  displayChannel.set(inputBuffer.getChannelData(0));

  const microphoneChannel = new Float32Array(frameCount);
  if (inputBuffer.numberOfChannels > 1) {
    microphoneChannel.set(inputBuffer.getChannelData(1));
  }

  return [displayChannel, microphoneChannel];
}

function encodeWav(channels: Float32Array[], sampleRate: number): Blob {
  const channelCount = Math.max(channels.length, 1);
  const frameCount = channels[0]?.length ?? 0;
  const bytesPerSample = 2;
  const blockAlign = channelCount * bytesPerSample;
  const buffer = new ArrayBuffer(44 + frameCount * blockAlign);
  const view = new DataView(buffer);

  const writeString = (offset: number, value: string) => {
    for (let i = 0; i < value.length; i += 1) {
      view.setUint8(offset + i, value.charCodeAt(i));
    }
  };

  writeString(0, "RIFF");
  view.setUint32(4, 36 + frameCount * blockAlign, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, channelCount, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * blockAlign, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, frameCount * blockAlign, true);

  let offset = 44;
  for (let frameIndex = 0; frameIndex < frameCount; frameIndex += 1) {
    for (let channelIndex = 0; channelIndex < channelCount; channelIndex += 1) {
      const sample = Math.max(-1, Math.min(1, channels[channelIndex]?.[frameIndex] ?? 0));
      view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
      offset += bytesPerSample;
    }
  }

  return new Blob([buffer], { type: "audio/wav" });
}

export async function startBrowserCallRecording(): Promise<BrowserCallRecorder> {
  if (typeof window === "undefined" || !navigator.mediaDevices) {
    throw new Error("Browser recording is not available in this environment.");
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
  const merger = audioContext.createChannelMerger(2);
  const processor = audioContext.createScriptProcessor(4096, 2, 2);
  const silentGain = audioContext.createGain();
  silentGain.gain.value = 0;

  const displayChunks: Float32Array[] = [];
  const microphoneChunks: Float32Array[] = [];

  displaySource.connect(merger, 0, 0);
  microphoneSource.connect(merger, 0, 1);
  merger.connect(processor);
  processor.connect(silentGain);
  silentGain.connect(audioContext.destination);

  processor.onaudioprocess = (event) => {
    const [displayChunk, microphoneChunk] = captureChannels(event.inputBuffer);
    displayChunks.push(displayChunk);
    microphoneChunks.push(microphoneChunk);
  };

  const cleanup = async () => {
    processor.disconnect();
    merger.disconnect();
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

      const totalLength = displayChunks.reduce((sum, chunk) => sum + chunk.length, 0);
      const mergedDisplay = new Float32Array(totalLength);
      const mergedMicrophone = new Float32Array(totalLength);
      let offset = 0;
      for (let index = 0; index < displayChunks.length; index += 1) {
        const displayChunk = displayChunks[index];
        const microphoneChunk = microphoneChunks[index];
        mergedDisplay.set(displayChunk, offset);
        mergedMicrophone.set(microphoneChunk, offset);
        offset += displayChunk.length;
      }

      if (mergedDisplay.length === 0) {
        throw new Error("No audio was captured. Make sure Meet tab audio is shared.");
      }

      return encodeWav([mergedDisplay, mergedMicrophone], audioContext.sampleRate);
    },
    cancel: async () => {
      await cleanup();
    },
  };
}
