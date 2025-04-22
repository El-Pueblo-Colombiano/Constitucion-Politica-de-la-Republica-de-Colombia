# Usar Node.js como imagen base
FROM node:18

# Establecer directorio de trabajo
WORKDIR /El-Pueblo-Colombiano

# Copiar package.json y package-lock.json (si existen)
COPY package*.json ./

# Instalar mintlify globalmente
RUN npm install -g mintlify@latest

# Copiar el resto de la documentación
COPY . .

# Exponer puerto 3000
EXPOSE 3000

# Comando para ejecutar mintlify
CMD ["mintlify", "dev"]