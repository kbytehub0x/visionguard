import sys
import platform
import json
import cv2
import numpy as np

def verify_graviton_environment():
    # NOTE: This is a container health check only.
    # Full COOL benchmark (10,000 frames, 1280x720) is in benchmarks/run_benchmark.py
    arch = platform.machine()
    system = platform.system()
    cv_version = cv2.__version__
    build_info = cv2.getBuildInformation()

    is_arm64 = arch.lower() in ["aarch64", "arm64"]
    neon_enabled = "NEON" in build_info
    kleidicv_present = "KLEIDICV" in build_info or "WITH_KLEIDICV=ON" in build_info
    num_threads = cv2.getNumThreads()
    
    dummy_frame = np.random.randint(0, 256, (720, 1280), dtype=np.uint8)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    
    start_tick = cv2.getTickCount()
    for _ in range(50):
        _ = clahe.apply(dummy_frame)
    end_tick = cv2.getTickCount()
    
    elapsed_sec = (end_tick - start_tick) / cv2.getTickFrequency()
    avg_latency_ms = (elapsed_sec / 50.0) * 1000.0

    report = {
        "status": "PASS" if is_arm64 and neon_enabled else "DEGRADED",
        "architecture": arch,
        "os": system,
        "opencv_version": cv_version,
        "neon_accelerated": neon_enabled,
        "kleidicv_compiled": kleidicv_present,
        "active_threads": num_threads,
        "bench_clahe_720p_avg_ms": round(avg_latency_ms, 3)
    }

    print(json.dumps(report, indent=2))
    
    if not is_arm64:
        sys.stderr.write("WARNING: Container is running on x86, not Graviton ARM64!\n")
    return report

if __name__ == "__main__":
    verify_graviton_environment()
