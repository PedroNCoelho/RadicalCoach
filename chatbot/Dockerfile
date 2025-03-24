FROM node:23
RUN mkdir /app
WORKDIR /app
COPY package.json package-lock.json* /app
RUN npm cache clean --force
RUN  npm install
COPY . /app
EXPOSE 5000
RUN apt update && apt install -y \
	chromium net-tools iputils-ping  vim ffmpeg libsm6 libxext6
RUN chown node:node /app
RUN chmod 755 -R /app/videos_recebidos/
USER node
CMD ["npm", "start"]
