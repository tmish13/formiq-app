import init, { Point, calculate_angle, calculate_distance, is_point_in_range } from './pose_calculations';

let isInitialized = false;

export async function initializeWasm() {
    if (!isInitialized) {
        await init();
        isInitialized = true;
    }
}

export class PoseCalculator {
    static async calculateAngle(p1: { x: number; y: number }, p2: { x: number; y: number }, p3: { x: number; y: number }): Promise<number> {
        await initializeWasm();
        const point1 = new Point(p1.x, p1.y);
        const point2 = new Point(p2.x, p2.y);
        const point3 = new Point(p3.x, p3.y);
        return calculate_angle(point1, point2, point3);
    }

    static async calculateDistance(p1: { x: number; y: number }, p2: { x: number; y: number }): Promise<number> {
        await initializeWasm();
        const point1 = new Point(p1.x, p1.y);
        const point2 = new Point(p2.x, p2.y);
        return calculate_distance(point1, point2);
    }

    static async isPointInRange(point: { x: number; y: number }, center: { x: number; y: number }, radius: number): Promise<boolean> {
        await initializeWasm();
        const pointObj = new Point(point.x, point.y);
        const centerObj = new Point(center.x, center.y);
        return is_point_in_range(pointObj, centerObj, radius);
    }
} 