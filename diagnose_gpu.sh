#!/bin/bash
# =============================================================================
# Diagnóstico GPU - AnonLFI
# =============================================================================

echo "🔍 Diagnóstico de GPU para AnonLFI"
echo "=================================="

# 1. Verificar NVIDIA driver
echo -e "\n1. Driver NVIDIA:"
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi --query-gpu=name,driver_version --format=csv
    echo "CUDA Version suportada:"
    nvidia-smi | grep "CUDA Version" | head -1
else
    echo "❌ nvidia-smi não encontrado. Driver NVIDIA não instalado."
fi

# 2. Verificar Docker + NVIDIA
echo -e "\n2. Docker NVIDIA Runtime:"
if docker --version >/dev/null 2>&1; then
    echo "✅ Docker instalado: $(docker --version)"
    
    # Verificar se nvidia-container-toolkit está instalado
    if dpkg -l | grep -q nvidia-container-toolkit; then
        echo "✅ NVIDIA Container Toolkit instalado"
    else
        echo "❌ NVIDIA Container Toolkit NÃO instalado"
    fi
    
    # Testar runtime NVIDIA
    if docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi 2>/dev/null | grep -q "CUDA Version"; then
        echo "✅ Docker + NVIDIA funcionando"
        docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi | head -10
    else
        echo "❌ Docker NVIDIA runtime com problemas"
    fi
else
    echo "❌ Docker não instalado"
fi

# 3. Testar CuPy com CUDA 12.8 no container GPU
echo -e "\n3. Teste CuPy no Container:"
docker run --rm --gpus all kapelinsky/anon:gpu python -c "
try:
    import cupy
    import torch
    print('PyTorch CUDA:', torch.cuda.is_available())
    print('PyTorch CUDA device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')
    a = cupy.array([1.0, 2.0])
    result = (a * a).sum()
    cupy.cuda.Stream.null.synchronize()
    print('✅ CuPy funcionando:', float(result))
except Exception as e:
    print('❌ CuPy erro:', e)
" 2>/dev/null || echo "❌ Não foi possível testar o container GPU"

# 4. Verificar versão CUDA suportada pela GPU
echo -e "\n4. Versão CUDA suportada:"
if command -v nvidia-smi >/dev/null 2>&1; then
    nvidia-smi | grep -i "cuda version" || echo "Versão CUDA não detectada"
fi

echo -e "\n🔧 Solução para Docker NVIDIA:"
echo "O problema é que o Docker não está configurado para usar GPU."
echo ""
echo "1. Instalar NVIDIA Container Toolkit:"
echo "   curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg"
echo "   curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list"
echo "   sudo apt update"
echo "   sudo apt install -y nvidia-container-toolkit"
echo ""
echo "2. Configurar Docker daemon:"
echo "   sudo nvidia-ctk runtime configure --runtime=docker"
echo "   sudo systemctl restart docker"
echo ""
echo "3. Testar:"
echo "   docker run --rm --gpus all nvidia/cuda:12.8.0-base-ubuntu22.04 nvidia-smi"
echo ""  
echo "4. Depois teste AnonLFI:"
echo "   ./run.sh --gpu arquivo.txt"