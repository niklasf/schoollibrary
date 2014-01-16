var express = require('express');
var mongoose = require('mongoose');
var mongooseAutoIncrement = require('mongoose-auto-increment');
var crypto = require('crypto');
var connectBasicAuth = require('connect-basic-auth');
var childProcess = require('child_process');
var byline = require('byline');

mongoose.connect('mongodb://localhost/test');
mongooseAutoIncrement.initialize(mongoose.connection);

var bookSchema = mongoose.Schema({
    title: String,
    authors: String,
    topic: String,
    keywords: String,
    signature: String,
    location: String,
    isbn: String,
    year: Number,
    publisher: String,
    placeOfPublication: { type: String, default: '' },
    volume: Number,
    lendable: Boolean,
    lending: {
        lentBy: String,
        lentSince: Date,
        lentForDays: Number
    }
});

bookSchema.plugin(mongooseAutoIncrement.plugin, 'Book');

var Book = mongoose.model('Book', bookSchema);

var app = express();
app.use(express.logger());
app.use(express.json());
app.use(express.urlencoded());

app.use(connectBasicAuth(function (credentials, req, res, next) {
    req.groups = [];

    var authProcess = childProcess.spawn('/etc/schoollibrary/auth.sh', [
        credentials.username,
        credentials.password
    ]);

    var auth = byline(authProcess.stdout, {
        keepEmptyLines: false
    });

    auth.on('data', function (group) {
        req.groups.push(group.toString('utf-8'));
    });

    authProcess.on('close', function () {
        if (req.groups.length) {
            req.user = credentials.username;
            next();
        } else {
            next('Authentication required');
        }
    });
}, 'Authentication required'));

app.all('*', function (req, res, next) {
    req.requireAuthorization(req, res, next);
});

app.all('*', (function () {
    var secret = crypto.randomBytes(64);

    return function (req, res, next) {
        req.csrf = crypto.createHmac('sha256', secret)
            .update(req.user)
            .digest('hex');

        if ('GET' == req.method || 'HEAD' == req.method || 'OPTIONS' == req.method) {
            return next();
        }

        var token = (req.body && req.body._csrf)
            || (req.query && req.query._csrf)
            || req.headers['x-csrf-token']
            || req.headers['x-xsrf-token'];

        if (token && token === req.csrf) {
            next();
        } else {
            return res.send(403);
        }
    };
})());

app.get('/', function (req, res) {
    res.json({
        user: req.user,
        _csrf: req.csrf
    });
});

app.get('/users/', function (req, res) {
    res.setHeader('Content-Type', 'text/plain');
    var users = childProcess.spawn('/etc/schoollibrary/users.sh');
    users.stdout.pipe(res);
});

app.get('/books/', function (req, res) {
    Book.find(function (err, books) {
        if (err) throw err;

        response = { }

        for (var i = 0; i < books.length; i++) {
            response[books[i].id] = books[i];
        }

        res.json(response);
    });
});

app.post('/books/', function (req, res) {
    // TODO
});

app.get('/books/:id/', function (req, res) {
    Book.findById(req.params.id, function (err, book) {
        if (err) throw err;

        if (!book) {
            return res.send(404);
        }

        res.json(book);
    });
});

app.put('/books/:id/', function (req, res) {
    Book.findById(req.params.id, function (err, book) {
        if (err) throw err;

        if (!book) {
            return res.send(404);
        }

        book.title = req.body.title;
        // TODO

        book.save(function (err) {
            if (err) {
                return res.send(400, err);
            }

            res.send(book);
        });
    });
});

app.post('/books/:id/lending', function (req, res) {
    // TODO
});

app.delete('/books/:id/lending', function (req, res) {
    // TODO
});

var port = parseInt(process.env.PORT) || 5000;
app.listen(port, function () {
    console.log('Listening on port ' + port + ' ...');
});
