# Imager

	This project is based on cyclone.io default template.
    It is an image hosting application. It uses Redis to store metadata and filesystem to store the image itself.
    This application is quite naive in terms of ranking and throttle control. Images can be liked/disliked, the number of hits is accounted but there's plenty of room to improve filtering and throttling. Throttle control is configured on 1 click per hour per image (for like/dislike but can be extended to other actions)
    
# Running

You can use supervisord or another process supervisor to run imager/start.sh script or raw twistd command instead.

Install cyclone and txmetrics with pip

Clone this repository or download the tar.gz/zip file

For development and testing:

    twistd -n cyclone --help
    twistd -n cyclone -r imager.web.Application [--help]

For production:

    twistd cyclone \
    	   --logfile=/var/log/imager.log \
    	   --pidfile=/var/run/imager.pid \
	   -r imager.web.Application

Don't forget to change the base_domain and filestore path at imager.conf. Most of the /tmp filesystems are ram based and used only for testing.

If you want to use nginx in front of it, explore the configuration files at scripts/, change the xheaders option at imager.conf to true and create a vhost on nginx that take care about the body size like this:

    server {
        listen   80;
        server_name  yourservername

        access_log  /var/log/nginx/yourservername.access.log;

        location / {
                root   /var/www/yourservername/;
                index  index.html index.htm;
                proxy_pass                  http://127.0.0.1:8888;
                proxy_redirect              off;

                proxy_set_header            Host            $host;
                proxy_set_header            X-Real-IP       $remote_addr;
                proxy_set_header            X-Forwarded-For $remote_addr;

                client_max_body_size        5M;
                client_body_buffer_size     5M;

                proxy_connect_timeout       30;
                proxy_send_timeout          30;
                proxy_read_timeout          30;

                proxy_buffer_size           4k;
                proxy_buffers               4 32k;
                proxy_busy_buffers_size     64k;
                proxy_temp_file_write_size  64k;

        }

    }


### Cookie Secret

The current cookie secret key in ``imager.conf`` was generated during the
creation of this package. However, if you need a new one, you may run the
``scripts/cookie_secret.py`` script to generate a random key.

## Credits

(c) 2013 
    - [gleicon](http://blog.7co.cc)
    - [cyclone](http://github.com/fiorix/cyclone) web server.
