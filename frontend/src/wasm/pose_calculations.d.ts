export class Point {
    constructor(x: number, y: number);
    x(): number;
    y(): number;
}

export function calculate_angle(p1: Point, p2: Point, p3: Point): number;
export function calculate_distance(p1: Point, p2: Point): number;
export function is_point_in_range(point: Point, center: Point, radius: number): boolean; 