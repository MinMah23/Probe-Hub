# Probe Hub

This repository contains the static and dynamic analysis probes developed and used for the **MASc thesis** of Mina Mahdipour.

These probes extract architectural and quality information from Java projects and export it in a unified JSON graph format that can be directly imported into an **SST (Single Source of Truth)** server for visualization and analysis.

### Prerequisites

1. An **SST server** must be up and running.  
   The easiest way is to use the official Docker image:

   ```bash
   docker run -d -p 8080:8080 --name sst acedesign/sst/sst:latest