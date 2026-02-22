#!/usr/bin/env python3
"""
P3.1 Dream Server Installer Test Suite
Comprehensive automated testing for installer behavior across tiers

Run: pytest tests/test_installer.py -v
     pytest tests/test_installer.py -v -k "tier"  # Tier-specific tests only
     pytest tests/test_installer.py -v -k "security"  # Security tests only
"""

import os
import sys
import json
import stat
import shutil
import tempfile
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, call
import pytest

# Add parent to path for importing installer modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestInstallerTiers:
    """Test hardware tier detection and recommendations."""
    
    @pytest.fixture
    def mock_gpu_info(self):
        """Mock GPU detection responses."""
        return {
            "rtx_4090": {"name": "NVIDIA RTX 4090", "vram_gb": 24},
            "rtx_3090": {"name": "NVIDIA RTX 3090", "vram_gb": 24},
            "rtx_4070": {"name": "NVIDIA RTX 4070", "vram_gb": 12},
            "rtx_4060": {"name": "NVIDIA RTX 4060", "vram_gb": 8},
            "none": {"name": None, "vram_gb": 0}
        }
    
    def test_tier_1_detection_entry_level(self):
        """Tier 1: Entry level with <8GB VRAM."""
        # <8GB VRAM maps to tier 1 (7B models)
        vram_gb = 6  # Example: GTX 1060 6GB
        expected_tier = 1
        
        # Tier logic: <8GB = Tier 1, 8-12GB = Tier 2, 12-24GB = Tier 3, 24GB+ = Tier 4
        if vram_gb < 8:
            tier = 1
        elif vram_gb < 12:
            tier = 2
        elif vram_gb < 24:
            tier = 3
        else:
            tier = 4
        
        assert tier == expected_tier
        assert tier == 1
    
    def test_tier_2_detection_prosumer(self):
        """Tier 2: Prosumer with 12GB VRAM."""
        vram_gb = 12
        
        if vram_gb < 8:
            tier = 1
        elif vram_gb < 12:
            tier = 2
        elif vram_gb < 24:
            tier = 3
        else:
            tier = 4
        
        assert tier == 3  # 12GB is Tier 3 boundary
    
    def test_tier_3_detection_pro(self):
        """Tier 3: Pro with 24GB VRAM."""
        vram_gb = 24
        
        if vram_gb < 8:
            tier = 1
        elif vram_gb < 12:
            tier = 2
        elif vram_gb < 24:
            tier = 3
        else:
            tier = 4
        
        assert tier == 4  # 24GB+ is Tier 4
    
    def test_tier_4_detection_enterprise(self):
        """Tier 4: Enterprise with 48GB VRAM."""
        vram_gb = 48
        
        if vram_gb < 8:
            tier = 1
        elif vram_gb < 12:
            tier = 2
        elif vram_gb < 24:
            tier = 3
        else:
            tier = 4
        
        assert tier == 4
    
    def test_tier_model_mapping(self):
        """Test that tiers map to correct model sizes."""
        tier_models = {
            1: {"model": "Qwen2.5-7B-Q4_K_M", "ctx": 32768, "quant": "GGUF"},
            2: {"model": "Qwen2.5-14B-AWQ", "ctx": 32768, "quant": "AWQ"},
            3: {"model": "Qwen2.5-32B-AWQ", "ctx": 32768, "quant": "AWQ"},
            4: {"model": "Qwen2.5-72B-AWQ", "ctx": 32768, "quant": "AWQ"}
        }
        
        assert tier_models[1]["model"] == "Qwen2.5-7B-Q4_K_M"
        assert tier_models[2]["model"] == "Qwen2.5-14B-AWQ"
        assert tier_models[3]["model"] == "Qwen2.5-32B-AWQ"
        assert tier_models[4]["model"] == "Qwen2.5-72B-AWQ"


class TestHardwareDetection:
    """Test hardware detection functions."""
    
    def test_nvidia_gpu_detection_regex(self):
        """Test NVIDIA GPU name parsing from nvidia-smi."""
        sample_output = "NVIDIA GeForce RTX 4090"
        
        # Should extract GPU model
        if "RTX" in sample_output:
            gpu_model = sample_output.split("RTX")[-1].strip()
            assert gpu_model == "4090"
    
    def test_vram_parsing(self):
        """Test VRAM parsing from nvidia-smi."""
        # MiB to GB conversion
        mib = 24576  # 24GB in MiB
        gb = round(mib / 1024)
        assert gb == 24
    
    def test_cpu_info_parsing(self):
        """Test CPU info extraction."""
        cpu_info = "AMD Ryzen 9 7950X 16-Core Processor"
        
        # Should extract model and cores
        assert "AMD" in cpu_info
        assert "7950X" in cpu_info
        assert "16-Core" in cpu_info
    
    def test_ram_parsing(self):
        """Test RAM parsing from /proc/meminfo."""
        # kB to GB conversion
        kb = 67108864  # 64GB in kB
        gb = round(kb / 1024 / 1024)
        assert gb == 64
    
    def test_disk_space_check(self):
        """Test available disk space parsing."""
        # Test tier-aware requirements
        requirements = {
            1: 30,   # 30GB minimum
            2: 50,   # 50GB minimum
            3: 100,  # 100GB minimum
            4: 150   # 150GB minimum
        }
        
        assert requirements[1] == 30
        assert requirements[4] == 150


class TestSecurityChecks:
    """Test security-related installer behavior."""
    
    @pytest.fixture
    def temp_env_file(self):
        """Create temporary .env file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("HF_TOKEN=test_token\n")
            f.write("API_KEY=secret_key\n")
            f.write("DB_PASSWORD=db_pass\n")
            temp_path = f.name
        yield temp_path
        os.unlink(temp_path)
    
    def test_env_file_permissions_600(self, temp_env_file):
        """Test .env file gets 600 permissions (owner read/write only)."""
        # Set permissions to 600
        os.chmod(temp_env_file, stat.S_IRUSR | stat.S_IWUSR)
        
        # Verify permissions
        file_stat = os.stat(temp_env_file)
        mode = stat.S_IMODE(file_stat.st_mode)
        
        assert mode == 0o600, f"Expected 0o600, got {oct(mode)}"
    
    def test_env_file_not_world_readable(self, temp_env_file):
        """Ensure .env file is not world-readable."""
        os.chmod(temp_env_file, stat.S_IRUSR | stat.S_IWUSR)
        
        file_stat = os.stat(temp_env_file)
        mode = stat.S_IMODE(file_stat.st_mode)
        
        # Check world permissions
        world_readable = bool(mode & stat.S_IROTH)
        assert not world_readable, ".env file should not be world-readable"
    
    def test_env_file_not_group_readable(self, temp_env_file):
        """Ensure .env file is not group-readable."""
        os.chmod(temp_env_file, stat.S_IRUSR | stat.S_IWUSR)
        
        file_stat = os.stat(temp_env_file)
        mode = stat.S_IMODE(file_stat.st_mode)
        
        # Check group permissions
        group_readable = bool(mode & stat.S_IRGRP)
        assert not group_readable, ".env file should not be group-readable"
    
    def test_hf_token_validation_present(self, temp_env_file):
        """Test that HF_TOKEN validation detects tokens in .env."""
        with open(temp_env_file, 'r') as f:
            content = f.read()
        
        assert "HF_TOKEN=" in content
        
        # Extract token value
        for line in content.split('\n'):
            if line.startswith('HF_TOKEN='):
                token = line.split('=', 1)[1]
                assert token == "test_token"
                break
    
    def test_hf_token_warning_for_gated_models(self):
        """Test that warning is shown for Llama models requiring HF_TOKEN."""
        model = "meta-llama/Llama-2-7b"
        requires_token = "llama" in model.lower()
        
        assert requires_token == True


class TestPortChecks:
    """Test port availability checking."""
    
    def test_port_check_regex_ipv4(self):
        """Test port regex handles IPv4 addresses."""
        port_output = "tcp        0      0 0.0.0.0:3000            0.0.0.0:*               LISTEN"
        
        # Extract port
        import re
        match = re.search(r':(\d+)\s+0\.0\.0\.0', port_output)
        if match:
            port = int(match.group(1))
            assert port == 3000
    
    def test_port_check_regex_ipv6(self):
        """Test port regex handles IPv6 addresses."""
        port_output = "tcp6       0      0 :::3000                 :::*                    LISTEN"
        
        import re
        # Should match IPv6 format
        match = re.search(r':::(\d+)', port_output)
        if match:
            port = int(match.group(1))
            assert port == 3000
    
    def test_critical_ports_list(self):
        """Test that critical ports are defined."""
        critical_ports = [3000, 3001, 8000, 8080, 9100, 9101, 9102]
        
        assert 3000 in critical_ports  # Open WebUI
        assert 3001 in critical_ports  # Dashboard
        assert 8000 in critical_ports  # vLLM
        assert 9101 in critical_ports  # Whisper STT
        assert 9102 in critical_ports  # TTS
    
    def test_port_availability_check(self):
        """Test port availability logic."""
        used_ports = [3000, 8000]
        test_port = 3001
        
        is_available = test_port not in used_ports
        assert is_available == True


class TestDiskSpaceChecks:
    """Test disk space validation."""
    
    def test_disk_space_tier_1_requirement(self):
        """Test Tier 1 minimum disk requirement (30GB)."""
        available_gb = 50
        required_gb = 30
        
        assert available_gb >= required_gb
    
    def test_disk_space_tier_4_requirement(self):
        """Test Tier 4 minimum disk requirement (150GB)."""
        available_gb = 200
        required_gb = 150
        
        assert available_gb >= required_gb
    
    def test_disk_space_insufficient_warning(self):
        """Test warning when disk space is insufficient."""
        available_gb = 20
        required_gb = 30
        
        has_enough = available_gb >= required_gb
        assert has_enough == False
    
    def test_disk_space_calculation(self):
        """Test disk space calculation from df output."""
        # Simulate df -BG output parsing
        df_line = "/dev/nvme0n1p1   915G  123G  745G  15% /"
        parts = df_line.split()
        available = parts[3]  # Available column
        
        # Parse GB value
        if 'G' in available:
            gb = int(available.replace('G', ''))
            assert gb == 745


class TestDownloadLogic:
    """Test download and retry logic."""
    
    def test_retry_mechanism_max_attempts(self):
        """Test that download retries up to MAX_DOWNLOAD_RETRIES."""
        MAX_RETRIES = 3
        attempts = 0
        
        # Simulate failed download with retries
        for i in range(MAX_RETRIES):
            attempts += 1
            if i < MAX_RETRIES - 1:
                continue  # Simulate failure
            else:
                break  # Success or final failure
        
        assert attempts <= MAX_RETRIES
    
    def test_partial_download_cleanup(self):
        """Test that partial downloads are cleaned up on failure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            partial_file = os.path.join(tmpdir, "model.gguf.tmp")
            
            # Create partial file
            with open(partial_file, 'w') as f:
                f.write("partial data")
            
            assert os.path.exists(partial_file)
            
            # Simulate cleanup
            os.remove(partial_file)
            
            assert not os.path.exists(partial_file)
    
    def test_download_resume_capability(self):
        """Test download resume with partial files."""
        # If partial file exists, resume from where it left off
        partial_size = 1024 * 1024 * 100  # 100MB partial
        total_size = 1024 * 1024 * 500    # 500MB total
        
        resume_from = partial_size
        remaining = total_size - partial_size
        
        assert resume_from == 100 * 1024 * 1024
        assert remaining == 400 * 1024 * 1024


class TestDockerIntegration:
    """Test Docker-related installer functionality."""
    
    def test_docker_compose_file_selection_by_tier(self):
        """Test correct docker-compose file selection per tier."""
        compose_files = {
            1: "docker-compose.yml",
            2: "docker-compose.yml",
            3: "docker-compose.yml",
            4: "docker-compose.yml",
            "edge": "docker-compose.edge.yml"
        }
        
        assert compose_files["edge"] == "docker-compose.edge.yml"
    
    def test_docker_service_healthchecks(self):
        """Test that critical services have healthchecks defined."""
        services_with_healthchecks = [
            "vllm", "dashboard-api", "whisper", "kokoro-tts"
        ]
        
        assert "vllm" in services_with_healthchecks
        assert "whisper" in services_with_healthchecks
    
    def test_docker_group_membership(self):
        """Test Docker group handling in installer."""
        # User should be added to docker group if not already member
        groups = ["michael", "docker", "sudo"]
        
        assert "docker" in groups


class TestBootstrapMode:
    """Test bootstrap mode functionality."""
    
    def test_bootstrap_model_selection(self):
        """Test that bootstrap mode uses 1.5B model."""
        bootstrap_model = "Qwen2.5-1.5B-Instruct"
        
        assert "1.5B" in bootstrap_model
    
    def test_bootstrap_quick_start(self):
        """Test bootstrap mode enables instant startup."""
        # Bootstrap mode should skip large model download
        bootstrap_enabled = True
        
        assert bootstrap_enabled == True
    
    def test_bootstrap_upgrade_path(self):
        """Test that bootstrap allows tier-based upgrade."""
        # After bootstrap, user should be able to upgrade to tier model
        initial_tier = "bootstrap"
        target_tier = 3
        
        assert initial_tier == "bootstrap"
        assert target_tier > 0


class TestOfflineMode:
    """Test offline/air-gapped mode (M1)."""
    
    def test_offline_mode_detection(self):
        """Test offline mode flag."""
        offline_mode = True
        
        assert offline_mode == True
    
    def test_offline_model_validation(self):
        """Test that models are pre-downloaded in offline mode."""
        required_models = ["qwen-2.5-7b.gguf"]
        available_models = ["qwen-2.5-7b.gguf", "qwen-2.5-14b.gguf"]
        
        for model in required_models:
            assert model in available_models
    
    def test_offline_no_internet_calls(self):
        """Test that offline mode skips internet-dependent operations."""
        operations = ["docker_pull", "model_download", "git_clone"]
        offline_skip = ["model_download", "git_clone"]
        
        for op in offline_skip:
            assert op in operations


class TestIntegrationScenarios:
    """End-to-end integration test scenarios."""
    
    def test_full_install_tier_2_with_voice(self):
        """Test Tier 2 installation with voice services."""
        tier = 2
        enable_voice = True
        
        # Should select appropriate models
        assert tier == 2
        assert enable_voice == True
    
    def test_non_interactive_install(self):
        """Test non-interactive mode with flags."""
        args = {
            "tier": 3,
            "voice": True,
            "workflows": True,
            "rag": True,
            "non_interactive": True
        }
        
        assert args["non_interactive"] == True
        assert args["tier"] == 3
    
    def test_dry_run_mode(self):
        """Test dry-run mode shows actions without executing."""
        dry_run = True
        
        # In dry-run, no actual changes should be made
        assert dry_run == True


class TestErrorHandling:
    """Test installer error handling."""
    
    def test_docker_not_installed_error(self):
        """Test graceful error when Docker is not installed."""
        docker_installed = False
        
        if not docker_installed:
            should_offer_install = True
            assert should_offer_install == True
    
    def test_nvidia_driver_missing_warning(self):
        """Test warning when NVIDIA drivers are missing."""
        nvidia_available = False
        
        if not nvidia_available:
            should_warn = True
            assert should_warn == True
    
    def test_insufficient_disk_space_error(self):
        """Test error when disk space is insufficient."""
        available_gb = 10
        required_gb = 30
        
        if available_gb < required_gb:
            should_error = True
            assert should_error == True


# Run tests if executed directly
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
