#1. python test_gpu.py

import torch

# Check if CUDA is available
if torch.cuda.is_available():
    print("CUDA is available. PyTorch can use the GPU.")
    
    # Get the name of the GPU
    gpu_name = torch.cuda.get_device_name(0)
    print(f"Using GPU: {gpu_name}")
    
    # Perform a simple operation on the GPU
    try:
        x = torch.tensor([1.0, 2.0, 3.0], device='cuda')  # Create tensor on GPU
        y = torch.tensor([4.0, 5.0, 6.0], device='cuda')  # Create another tensor on GPU
        z = x + y  # Perform operation on GPU
        print("GPU computation successful. Result:", z)
    except Exception as e:
        print("An error occurred while performing GPU computation:", e)
else:
    print("CUDA is not available. PyTorch is using the CPU.")



  