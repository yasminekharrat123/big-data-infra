import { Request, Response, NextFunction } from 'express';
import { mainService } from '../services/mainService';

export class MainController {
    randomGreeting(req: Request, res: Response, next: NextFunction) {
        try {
            const greeting = mainService.randomGreeting();
            res.json({ greeting });
        } catch (error: any) {
            next(error);
        }
    }

    cpuIntensive(req: Request, res: Response, next: NextFunction) {
        try {
        const n = parseInt(req.query.n as string) || 40;
        const result = mainService.fibonacci(n);
        res.json({ message: `Fibonacci(${n}) = ${result}` });
        } catch (error: any) {
        next(error);
        }
    }

    randomError(req: Request, res: Response, next: NextFunction) {
        try {
        const result = mainService.randomError();
        res.json(result);
        } catch (error: any) {
        next(error);
        }
    }

    memoryLeak(req: Request, res: Response, next: NextFunction) {
        try {
        const result = mainService.memoryLeak();
        res.json(result);
        } catch (error: any) {
        next(error);
        }
    }
}

export const mainController = new MainController();