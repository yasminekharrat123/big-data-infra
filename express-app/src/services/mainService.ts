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
        if (random < 0.3) {
        throw new Error('Random server error occurred!');
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