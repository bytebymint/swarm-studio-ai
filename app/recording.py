"""Deterministic browser frames, a continuous task-aware lens, and local MP4 encoding."""
import base64
from bisect import bisect_left, bisect_right
import io
import json
import os
import threading
import uuid
from fractions import Fraction
from pathlib import Path

from PySide6.QtCore import QThread, Signal


def synthesize(events, start, samples, sample_rate=48000):
    """A bounded audio block. No microphone or desktop audio is captured."""
    import numpy as np
    output = np.zeros((2, samples), dtype=np.float32)
    times = (np.arange(samples, dtype=np.float64) + start) / sample_rate
    notes = [164.81, 185, 207.65, 246.94, 277.18]
    for event in events:
        kind, at = event['kind'], event['time']
        duration = .9 if kind == 'complete' else .09 if kind in ('type', 'click') else .2
        if at >= times[-1] + 1/sample_rate or at + duration < times[0]:
            continue
        t = times-at
        mask = (t >= 0) & (t < duration)
        local = t[mask]
        if kind in ('type', 'click'):
            hz = 190 if kind == 'type' else 420
            # Analytic noise avoids random state depending on block boundaries.
            noise = np.sin((np.floor(local*sample_rate)+at*7919)*12.9898)*43758.5453
            noise = 2*(noise-np.floor(noise))-1
            wave = (np.sin(2*np.pi*hz*local)*.6 + noise*.4)*np.exp(-local*95)
        else:
            tones = [164.81, 207.65, 246.94, 329.63] if kind == 'complete' else [notes[min(4,int(event['x']*5))]*2]
            wave = sum(np.sin(2*np.pi*hz*local) for hz in tones)/len(tones)*np.exp(-local*(5 if kind == 'complete' else 22))
        wave *= min(1,max(0,event.get('volume',.25)))*.13
        pan = min(1,max(0,event.get('x',.5)))
        output[0,mask] += wave*(1-pan)**.5
        output[1,mask] += wave*pan**.5
    return np.ascontiguousarray(np.clip(output,-.95,.95))
