# The image a run happens inside. Copy this OUTSIDE the repository, build it once as root,
# and name it in /etc/neuralscreen-runner/policy.toml:
#
#   install -d /opt/neuralscreen/image
#   install -m 0644 tools/runner_container/Dockerfile /opt/neuralscreen/image/
#   podman build -t localhost/neuralscreen-runner:1 /opt/neuralscreen/image
#
# Why outside the repo: if this file lived in the tree, a commit could add a package, a pip
# install, a hook, and the toolchain would no longer be the one you reviewed. The policy
# pins the image by tag; pin it by digest if you would rather it never move.
#
# The NVIDIA userspace libraries are NOT here. They come from the host at run time through
# the container toolkit, which is the only way to be sure the image's libraries match the
# kernel module you are actually running:
#
# These two ARE system packages and a system file, which is the whole reason the container is
# not the default here - see the policy. If you do want it:
#
#   sudo pacman -S nvidia-container-toolkit
#   nvidia-ctk cdi generate --output=$HOME/.config/cdi/nvidia.yaml    # user-level, no sudo
#   podman run --rm --device nvidia.com/gpu=all \
#        --cdi-spec-dir=$HOME/.config/cdi localhost/neuralscreen-runner:1 \
#        vulkaninfo --summary        # should name the RTX 4080 SUPER
#
# Verify that before trusting a run: inside the sandbox the GPU is the whole point, and a
# container that silently fell back to software rendering would report believable timings.

FROM archlinux:base

# glslang is not optional: the port's shaders need GL_EXT_float_e4m3 and
# GL_NV_cooperative_matrix2, which wants 16.6.0 or newer.
RUN pacman -Syu --noconfirm && \
    pacman -S --noconfirm --needed \
        python uv git \
        vulkan-icd-loader vulkan-tools libglvnd \
        gcc cmake ninja glslang \
        xorg-server-xvfb && \
    pacman -Scc --noconfirm

# --headless still creates a window, hidden; SDL needs a video driver to do it, and Xvfb is
# the one the test suite already uses.
ENV SDL_VIDEODRIVER=x11
ENV DISPLAY=:99

WORKDIR /work
