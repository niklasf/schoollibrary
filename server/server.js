var express = require('express');
var mongoose = require('mongoose');
var mongooseAutoIncrement = require('mongoose-auto-increment');
var crypto = require('crypto');
var connectBasicAuth = require('connect-basic-auth');
var childProcess = require('child_process');
var byline = require('byline');
var validator = require('validator');
var fs = require('fs');

mongoose.connect('mongodb://localhost/schoollibrary');
mongooseAutoIncrement.initialize(mongoose.connection);

var bookSchema = mongoose.Schema({
    etag: {
        type: Number,
        required: true
    },
    title: {
        type: String,
        required: true,
        trim: true
    },
    authors: {
        type: String,
        default: '',
        trim: true
    },
    topic: {
        type: String,
        default: '',
        trim: true
    },
    keywords: {
        type: String,
        default: '',
        trim: true
    },
    signature: {
        type: String,
        default: '',
        trim: true
    },
    location: {
        type: String,
        default: '',
        trim: true
    },
    isbn: {
        type: String,
        default: '',
        trim: true,
        validate: function (isbn) {
            if (!isbn) {
                return true;
            } else {
                return validator.isISBN(isbn);
            }
        }
    },
    year: {
        type: Number,
        default: null
    },
    publisher: {
        type: String,
        default: '',
        trim: true
    },
    placeOfPublication: {
        type: String,
        default: '',
        trim: true
    },
    volume: {
        type: String,
        default: '',
        trim: true
    },
    lendable: {
        type: Boolean,
        default: true
    },
    lending: {
        user: {
            type: String,
            default: null,
            match: /[0-9A-Za-z\-\_\+\.]+@[0-9A-Za-z\-\_\.]+/
        },
        since: {
            type: Date,
            default: null
        },
        days: {
            type: Number,
            default: null,
            min: 0
        }
    }
});

bookSchema.pre('save', function (next) {
    this.isbn = validator.isISBN(this.isbn);
    next();
});

bookSchema.virtual('lent').get(function () {
    return !! (this.lending && this.lending.user);
});

bookSchema.plugin(mongooseAutoIncrement.plugin, 'Book');

var Book = mongoose.model('Book', bookSchema);

var authHook = '/etc/schoollibrary/auth.sh';
if (fs.existsSync('auth.sh')) {
    authHook = './auth.sh';
}
var usersHook = '/etc/schoollibrary/users.sh';
if (fs.existsSync('users.sh')) {
    usersHook = './users.sh';
}

var app = express();
app.use(express.logger());
app.use(express.json());
app.use(express.urlencoded());

app.use(connectBasicAuth(function (credentials, req, res, next) {
    req.groups = [];

    var authProcess = childProcess.spawn(authHook, [
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

            req.library_admin = req.groups.indexOf('library_admin') !== -1;
            req.library_modify = req.library_admin || req.groups.indexOf('library_modfiy') !== -1;
            req.library_delete = req.library_admin || req.groups.indexOf('library_delete') !== -1;
            req.library_lend = req.library_admin || req.groups.indexOf('library_lend') !== -1;

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
    var oldSecret = crypto.randomBytes(64);

    setInterval(function () {
        oldSecret = secret;
        secret = crypto.randomBytes(64);
    }, 1000 * 60 * 60 * 24);

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

        var oldCsrf = crypto.createHmac('sha256', secret)
            .update(req.user)
            .digest('hex');

        if (token && (token === req.csrf || token === oldCsrf)) {
            next();
        } else {
            return res.send(419);
        }
    };
})());

app.get('/', function (req, res) {
    res.json({
        user: req.user,
        groups: req.groups,
        _csrf: req.csrf
    });
});

app.get('/users/', function (req, res) {
    if (!req.library_lend) {
        return res.send(403);
    }

    res.setHeader('Content-Type', 'text/plain');
    var users = childProcess.spawn(usersHook);
    users.stdout.pipe(res);
});

app.get('/books/', function (req, res) {
    Book.find(function (err, books) {
        if (err) throw err;

        var etag = 0;
        var response = { }

        for (var i = 0; i < books.length; i++) {
            etag ^= books[i].etag;

            response[books[i].id] = books[i].toObject({ virtuals: true });

            if (!req.library_lend) {
                delete response[books[i].id].lending;
            }
        }

        res.setHeader('ETag', etag);
        res.json(response);
    });
});

app.post('/books/', function (req, res) {
    if (!req.library_modify) {
        return res.send(403);
    }

    var book = new Book();

    book.etag = crypto.randomBytes(4).readUInt32BE(0);
    book.title = req.body.title;
    book.authors = req.body.authors;
    book.topic = req.body.topic;
    book.keywords = req.body.keywords;
    book.signature = req.body.signature;
    book.location = req.body.location;
    book.isbn = req.body.isbn;
    book.year = parseInt(req.body.year, 10) || null;
    book.publisher = req.body.publisher;
    book.placeOfPublication = req.body.placeOfPublication;
    book.volume = req.body.volume;
    book.lendable = req.body.lendable;

    book.save(function (err) {
        if (err) {
            res.send(400, err);
        } else {
            res.setHeader('ETag', book.etag);
            res.json(book.toObject({ virtuals: true }));
        }
    });
});

app.get('/books/:id/', function (req, res) {
    Book.findById(req.params.id, function (err, book) {
        if (err) throw err;

        if (!book) {
            return res.send(404);
        }

        var response = book.toObject({ virtuals: true });

        if (!req.library_lend) {
            delete response.lending;
        }

        res.setHeader('ETag', book.etag);
        res.json(response);
    });
});

app.put('/books/:id/', function (req, res) {
    Book.findById(req.params.id, function (err, book) {
        if (err) throw err;

        if (!book) {
            return res.send(404);
        }

        if (!req.library_modify) {
            return res.send(403);
        }

        if (req.body.etag && req.body.etag !== book.etag) {
            return res.send(409);
        }

        book.etag = crypto.randomBytes(4).readUInt32BE(0);
        book.title = req.body.title;
        book.authors = req.body.authors;
        book.topic = req.body.topic;
        book.keywords = req.body.keywords;
        book.signature = req.body.signature;
        book.location = req.body.location;
        book.isbn = req.body.isbn;
        book.year = parseInt(req.body.year, 10) || null;
        book.publisher = req.body.publisher;
        book.placeOfPublication = req.body.placeOfPublication;
        book.volume = req.body.volume;
        book.lendable = req.body.lendable;

        book.save(function (err) {
            if (err) {
                return res.send(400, err);
            }

            res.setHeader('ETag', book.etag);
            res.send(book);
        });
    });
});

app.delete('/books/:id/', function (req, res) {
    Book.findById(req.params.id, function (err, book) {
        if (err) throw err;

        if (!book) {
            return res.send(404);
        }

        if (!req.library_delete) {
            return res.send(403);
        }

        book.remove(function (err, book) {
            if (err) throw err;
            return res.send(204);
        });
    });
});

app.get('/books/:id/lending', function (req, res) {
    Book.findById(req.params.id, function (err, book) {
        if (err) throw err;

        if (!book) {
            return res.send(404);
        }

        if (!book.lent) {
            return res.send(404);
        }

        if (!req.library_lend) {
            return res.send(403);
        }

        res.setHeader('ETag', book.etag);
        res.json(book.lending);
    });
});

app.post('/books/:id/lending', function (req, res) {
    Book.findById(req.params.id, function (err, book) {
        if (err) throw err;

        if (!book) {
            return res.send(404);
        }

        if (!req.library_lend) {
            return res.send(403);
        }

        if (req.body.etag && req.body.etag !== book.etag) {
            return res.send(409);
        }

        if (book.lent && book.lending.user !== req.body.user) {
            return res.send(412);
        }

        if (!req.body.user) {
            return res.send(400);
        }

        if (book.lending.user !== req.body.user) {
            book.lending.since = new Date();
        }

        book.etag = crypto.randomBytes(4).readUInt32BE(0);
        book.lending.user = req.body.user;
        book.lending.days = parseInt(req.body.days, 10) || 14;

        book.save(function (err) {
            if (err) {
                return res.send(400, err);
            }

            res.setHeader('ETag', book.etag);
            res.json(book.lending);
        });
    });
});

app.delete('/books/:id/lending', function (req, res) {
    Book.findById(req.params.id, function (err, book) {
        if (err) throw err;

        if (!book) {
            return res.send(404);
        }

        if (!book.lent) {
            return res.send(404);
        }

        if (!req.library_lend) {
            return res.send(403);
        }

        book.etag = crypto.randomBytes(4).readUInt32BE(0);
        book.lending.user = null;
        book.lending.since = null;
        book.lending.days = null;

        book.save(function (err) {
            if (err) {
                return res.send(400, err);
            } else {
                return res.send(204);
            }
        });
    });
});

var port = parseInt(process.env.PORT) || 5000;
app.listen(port, function () {
    console.log('Listening on port ' + port + ' ...');
});
