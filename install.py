
import subprocess
import platform
import launch


try:        
    subprocess.run(["aria2c", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    spec = True
except (subprocess.CalledProcessError, FileNotFoundError):
    spec = None

print("Checking requirements for CivitAI Browser")

if platform.system() == "Linux":
   if not spec or spec is None:
        print("Intalling aria2 using apt-get")
        launch.run("apt-get -qq update && apt-get -qq install -y aria2", desc="Installing requirements for CivitAI Browser - Aria2", errdesc=f"Couldn't install requirements for CivitAI Browser - Aria2")
        spec = True
   else:
        pass
elif platform.system() == "Darwin":
    if not spec or spec is None:
        print("Intalling aria2 using brew")
        launch.run("brew install aria2", desc="Installing requirements for CivitAI Browser - Aria2", errdesc=f"Couldn't install requirements for CivitAI Browser - Aria2")
        spec = True
    else:
        pass
elif platform.system() == "Windows":
    if not spec or spec is None:
        print("CivitAI Browser relies on aria2 for optimal performance and you're using Windows. To install aria2 on Windows, please search for a tutorial on YouTube on how to install aria2")
        spec = True
    else:
        pass

if not launch.is_installed("blake3"):
    launch.run_pip("install blake3", "requirements for CivitAI Browser - Blake3")
    spec = True

if spec:
    print("Requirements for CivitAI Browser installed")