import express, { Request, Response, NextFunction } from 'express';
import morgan from 'morgan';
import { mainController } from './controllers/mainController';

const app = express();
const port = process.env.PORT || 3000;


morgan.token('custom', (req: Request, res: Response) => {
const params = {
    query: req.query,
    body: req.body,
};
const responseBody = res.locals.responseBody || 'No response body';
const error = res.locals.error || 'No error';
return JSON.stringify({
    params,
    response: {
    status: res.statusCode,
    body: responseBody,
    },
    error,
});
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

app.use(
morgan(
    ':method :url :status :response-time ms - :res[content-length] bytes :custom'
)
);

// Routes
app.get('/', mainController.randomGreeting.bind(mainController));
app.get('/cpu', mainController.cpuIntensive.bind(mainController));
app.get('/error', mainController.randomError.bind(mainController));
app.get('/memory-leak', mainController.memoryLeak.bind(mainController));

// Error handling middleware
app.use((err: Error, req: Request, res: Response, next: NextFunction) => {
res.locals.error = err.message;
res.status(500).json({
    status:500,
    error: err.message });
});

app.listen(port, () => {
console.log(`Express app listening on http://localhost:${port}`);
});