import { HttpError } from "../errors/HttpError";

declare global {
    var leakArray: any[];
}

export class MainService {
    randomGreeting(): string {
        const greetings = ['Hello', 'Hi', 'Hey', 'Greetings', 'Salutations'];
        const words = ['mate', 'sailor', 'brother', 'friend', 'pal'];
        const randomGreetingsIndex = Math.floor(Math.random() * greetings.length);
        const randomWordIndex = Math.floor(Math.random() * words.length);
        const greeting = greetings[randomGreetingsIndex]+' '+words[randomWordIndex];
        return greeting
    }
    // CPU-intensive Fibonacci calculation
    fibonacci(n: number): number {
        if (n <= 1) return n;
        return this.fibonacci(n - 1) + this.fibonacci(n - 2);
    }

    // Random error generator
    randomError(): { message: string } {
        const random = Math.random();
        if (random < 0.5) {
        const errorTypes = [
            { status: 500, message: 'Internal Server Error' },
            { status: 401, message: 'Unauthorized: Invalid credentials provided' },
            { status: 403, message: 'Forbidden: Access to resource denied' },
            { status: 404, message: 'Not Found: Requested resource does not exist' },
            { status: 400, message: 'Bad Request: Invalid input parameters' },
        ];
        const selectedError = errorTypes[Math.floor(Math.random() * errorTypes.length)];
        throw new HttpError(selectedError.status, selectedError.message);
        }
        return { message: 'Operation successful' };
    }

    memoryLeak(): { message: string; leakSize: number } {
        // Initialize global array if not exists
        if (!global.leakArray) {
        global.leakArray = [];
        }
        // Add large objects to the array
        for (let i = 0; i < 10000; i++) {
        global.leakArray.push({
            id: i,
            data: new Array(1000).fill('leak').join(''),
        });
        }
        return { message: 'Memory leak triggered', leakSize: global.leakArray.length };
    }
}

export const mainService = new MainService();