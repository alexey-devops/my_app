# ./frontend/Dockerfile
FROM nginx:alpine

WORKDIR /usr/share/nginx/html

COPY --chown=nginx:nginx index.html .

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD wget --quiet --tries=1 --spider http://localhost || exit 1

CMD ["nginx", "-g", "daemon off;"]
