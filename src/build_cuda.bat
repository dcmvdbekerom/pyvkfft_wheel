
:: Clear old files:
cls
del build /q

:: Set compiler environment:
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\Community\VC\Auxiliary\Build\vcvarsall.bat" x64

:: Compilte PTX:
::nvcc --ptx --output-file="build\kernels.ptx" kernels.cu  

:: Compile DLL:
copy vkfft_cuda.cu vkfft_cuda.cpp
cl /LD /EHsc /Fe"build_cuda/vkfft_cuda.dll"  /O2 /IVkFFT\vkFFT /I"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\include" vkfft_cuda.cpp /link /LIBPATH:"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v11.8\lib\x64" cuda.lib cudart.lib nvrtc.lib

del build_cuda\vkfft_cuda.exp
del build_cuda\vkfft_cuda.lib
del vkfft_cuda.obj




:: Compile SO (using WSL):
::echo WSL g++ compile to .so...
::wsl -e g++ -shared -nolibc -nostdlib -lgcc -fPIC -o build/kernels.so kernels.cpp
::echo Done!

:: Clean up:
del vkfft_cuda.cpp
pause
