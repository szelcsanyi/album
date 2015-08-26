# Album

## Description
Simple, easy to use image gallery

### Installation
- create a virtualenv: virtualenv /path/to/virtualenv
- source /path/to/virtualenv/bin/activate
- git clone this repo to /path/to/album
- pip install -r /path/to/album/requirements.txt
- install uwsgi
- install apache or nginx

#### Config examples

###### uwsgi - album.ini
<pre>
[uwsgi]
vhost = true
plugins = python
master = true
enable-threads = true
processes = 2
wsgi-file = /path/to/album/album.py
virtualenv = /path/to/virtualenv
chdir = /path/to/album
touch-chain-reload = /path/to/album/reload
socket = 127.0.0.1:3031
uid = kepek
gid = kepek
lazy-apps = true
honour-stdin = true
</pre>

###### Apache2
<pre>
&lt;VirtualHost *:80&gt;
    ServerName alerts.yourdomain

    DocumentRoot /path/to/album

    &lt;Directory /path/to/album&gt;
        Options Indexes FollowSymLinks MultiViews
        AllowOverride None
        Order allow,deny
        allow from all
    &lt;/Directory&gt;

    &lt;Location /&gt;
        Options FollowSymLinks Indexes
        SetHandler uwsgi-handler
        uWSGISocket 127.0.0.1:3031
    &lt;/Location&gt;

    &lt;Location /static&gt;
        SetHandler none
    &lt;/Location&gt;
&lt;/VirtualHost&gt;
</pre>

###### Nginx
<pre>
server {
        listen   80;
        autoindex off;

        server_name alerts.yourdomain;

        location /static/ {
            alias /path/to/album/static/;
            expires max;
            log_not_found off;
        }

        location / {
                uwsgi_pass  127.0.0.1:3031;
                include     uwsgi_params;
        }
}
</pre>


## External resources
- [Flask](http://flask.pocoo.org/)
- [jQuery](https://jquery.com/)
- [JustifiedGallery](http://miromannino.github.io/Justified-Gallery/)
- [Colorbox](http://www.jacklmoore.com/colorbox/)
- [FineUploader](http://fineuploader.com/)
- [Rollbar](https://rollbar.com/)
- [Bootstrap](http://getbootstrap.com/)

## Contributing

1. Fork it
2. Create your feature branch (`git checkout -b my-new-feature`)
3. Commit your changes (`git commit -am 'Added some feature'`)
4. Push to the branch (`git push origin my-new-feature`)
5. Create new Pull Request

## License

* Freely distributable and licensed under the [MIT license](http://szelcsanyi.mit-license.org/2015/license.html).
* Copyright (c) 2015 Gabor Szelcsanyi

[![image](https://ga-beacon.appspot.com/UA-56493884-1/album/README.md)](https://github.com/szelcsanyi/album)

