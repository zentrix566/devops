FROM nginx:alpine

# 1. 删除默认配置和默认网页
RUN rm /etc/nginx/nginx.conf && rm -rf /usr/share/nginx/html/*

# 2. 复制自定义配置文件
COPY nginx.conf /etc/nginx/nginx.conf

# 3. 复制网页文件
# 首页放根目录
COPY index.html /usr/share/nginx/html/
# 子页面放 web 文件夹
COPY web/*.html /usr/share/nginx/html/

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]