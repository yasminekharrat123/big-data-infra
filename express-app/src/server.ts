import express, { Request, Response, NextFunction } from 'express';
import morgan from 'morgan';
import { mainController } from './controllers/mainController';
import { HttpError } from './errors/HttpError';

const app = express();
const port = process.env.PORT || 3000;


morgan.token('json', (req: Request, res: Response) => {
    const log = {
    method: req.method,
    url: req.url,
    status: res.statusCode,
    contentLength: res.getHeader('content-length') || '0',
    params: {
        query: req.query,
        body: req.body,
    },
    response: {
        status: res.statusCode,
        body: res.locals.responseBody || 'No response body',
    },
    error: res.locals.error || 'No error',
    };
    return JSON.stringify(log);
});

// Middleware to capture response body
app.use((req: Request, res: Response, next: NextFunction) => {
    const originalJson = res.json;
    res.json = function (body: any) {
    res.locals.responseBody = body;
    return originalJson.call(this, body);
    };
    next();
});

app.use(morgan(':json'));

// Routes
app.get('/', mainController.randomGreeting.bind(mainController));
app.get('/cpu', mainController.cpuIntensive.bind(mainController));
app.get('/error', mainController.randomError.bind(mainController));
app.get('/memory-leak', mainController.memoryLeak.bind(mainController));

// Error handling middleware
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
    res.locals.error = err.message; // Store error for Morgan
    if (err instanceof HttpError) {
    res.status(err.status).json({ error: err.message });
    } else {
    res.status(500).json({ error: err.message });
    }
});

app.listen(port, () => {
console.log(`Express app listening on http://localhost:${port}`);
});