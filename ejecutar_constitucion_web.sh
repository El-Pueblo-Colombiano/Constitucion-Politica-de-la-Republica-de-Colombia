#!/bin/bash

# Construir la imagen si no existe
podman build -t constitucion-politica-de-colombia .

# Ejecutar el contenedor con mintlify directamente
podman run -it --rm \
  -p 3000:3000 \
  constitucion-politica-de-colombia

