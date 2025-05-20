// Requires: p5.js (https://cdnjs.cloudflare.com/ajax/libs/p5.js/1.9.0/p5.min.js)
// Include this script in an HTML file with a canvas

// Layout & Animation parameters
const maxBins      = 25;   // Maximum resolution in either dimension
const speedFactor  = 3;    // ↑ bigger = slower bin updates

// Margins (pixels)
const leftMargin   = 200;
const topMargin    = 20;
const rightMargin  = 20;
const bottomMargin = 40;

// Colors
const bgColor      = '#181818';  // Dark gray background
const textColor    = '#0fbc7a';  // Bright teal text

let freqBins = maxBins;    // Start at full resolution
let timeBins = maxBins;

let phase = 0;             // 0 = both, 1 = frequency‑only, 2 = time‑only
let dir   = -1;            // -1 shrinking, +1 growing

// Base spectrogram at max resolution (constant throughout animation)
let baseSpectrogram = [];
let spectrogram     = [];

function setup() {
  createCanvas(800, 500);
  frameRate(12);
  generateBaseSpectrogram();   // one‑time noise at maxBins × maxBins
  downsampleSpectrogram();     // initial view
}

function draw() {
  background(bgColor);

  // UI Read‑outs
  fill(textColor);
  textSize(16);
  textAlign(LEFT, TOP);
  text(`Frequency Bins: ${freqBins}`, 10, 10);
  text(`Time Bins: ${timeBins}`,       10, 30);
  // Wrapped blurb inside left margin
  textSize(12);
  const blurb = 'Here is an example visual demonstrating the effect that bin sizes have on spectrogram trends and peaks. This is beneficial for seeing peaks on either frequency or time domains. Changing bin sizes is left up to the agent if not otherwise specified by the user. This creates some very interesting results!';
  text(blurb, 10, 55, leftMargin - 30, 180); // x, y, box width, box height for wrapping
  textSize(16);

  // Axis labels
  textSize(14);
  textAlign(CENTER);
  fill(textColor);
  const drawableW = width  - leftMargin - rightMargin;
  const drawableH = height - topMargin  - bottomMargin;
  text('Frequency bins (Hz) →', leftMargin + drawableW / 2, height - bottomMargin / 2);
  push();
  translate(leftMargin - 15, topMargin + drawableH / 2);
  rotate(-HALF_PI);
  text('Time bins (sec) ↑', 0, 0);
  pop();

  // Draw Spectrogram 
  const cellW = drawableW / freqBins;
  const cellH = drawableH / timeBins;

  for (let y = 0; y < timeBins; y++) {
    for (let x = 0; x < freqBins; x++) {
      const val      = spectrogram[y][x];          // 0 … 1
      const colorVal = map(val, 0, 1, 0, 255);
      fill(255 - colorVal, 50, colorVal);          // blue‑to‑red gradient
      rect(leftMargin + x * cellW, topMargin + y * cellH, cellW, cellH);
    }
  }

  // Update Bin Counts per Phase
  if (frameCount % speedFactor === 0) {
    switch (phase) {
      case 0: // Both dimensions animate together
        freqBins += dir;
        timeBins += dir;
        if (freqBins <= 1 || freqBins >= maxBins) {
          if (dir > 0 && freqBins >= maxBins) { phase = 1; dir = -1; }
          else if (dir < 0 && freqBins <= 1) { dir = 1; }
        }
        break;

      case 1: // Frequency only
        freqBins += dir;
        if (freqBins <= 1 || freqBins >= maxBins) {
          if (dir > 0 && freqBins >= maxBins) { phase = 2; dir = -1; }
          else if (dir < 0 && freqBins <= 1)  { dir = 1; }
        }
        break;

      case 2: // Time only
        timeBins += dir;
        if (timeBins <= 1 || timeBins >= maxBins) {
          if (dir > 0 && timeBins >= maxBins) { phase = 0; dir = -1; }
          else if (dir < 0 && timeBins <= 1)  { dir = 1; }
        }
        break;
    }

    // Constrain counts and refresh downsampled spectrogram
    freqBins = constrain(freqBins, 1, maxBins);
    timeBins = constrain(timeBins, 1, maxBins);
    downsampleSpectrogram();
  }
}

// Generate a fixed maxBins × maxBins noise matrix once
function generateBaseSpectrogram() {
  for (let t = 0; t < maxBins; t++) {
    const row = [];
    for (let f = 0; f < maxBins; f++) {
      row.push(noise(t * 0.6, f * 0.6));
    }
    baseSpectrogram.push(row);
  }
}

// Down‑sample baseSpectrogram by averaging blocks into current bin counts
function downsampleSpectrogram() {
  spectrogram = [];
  for (let t = 0; t < timeBins; t++) {
    const row = [];
    const tStart = floor(t * maxBins / timeBins);
    const tEnd   = floor((t + 1) * maxBins / timeBins);
    for (let f = 0; f < freqBins; f++) {
      const fStart = floor(f * maxBins / freqBins);
      const fEnd   = floor((f + 1) * maxBins / freqBins);
      let sum = 0, count = 0;
      for (let i = tStart; i < tEnd; i++) {
        for (let j = fStart; j < fEnd; j++) {
          sum += baseSpectrogram[i][j];
          count++;
        }
      }
      row.push(count ? sum / count : 0);
    }
    spectrogram.push(row);
  }
}
