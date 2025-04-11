use wasm_bindgen::prelude::*;

#[wasm_bindgen]
pub struct Point {
    x: f32,
    y: f32,
}

#[wasm_bindgen]
impl Point {
    #[wasm_bindgen(constructor)]
    pub fn new(x: f32, y: f32) -> Point {
        Point { x, y }
    }

    pub fn x(&self) -> f32 {
        self.x
    }

    pub fn y(&self) -> f32 {
        self.y
    }
}

#[wasm_bindgen]
pub fn calculate_angle(p1: Point, p2: Point, p3: Point) -> f32 {
    let v1 = Point::new(p1.x - p2.x, p1.y - p2.y);
    let v2 = Point::new(p3.x - p2.x, p3.y - p2.y);
    
    let dot_product = v1.x * v2.x + v1.y * v2.y;
    let v1_mag = (v1.x * v1.x + v1.y * v1.y).sqrt();
    let v2_mag = (v2.x * v2.x + v2.y * v2.y).sqrt();
    
    let cos_angle = dot_product / (v1_mag * v2_mag);
    let angle = cos_angle.acos();
    
    angle.to_degrees()
}

#[wasm_bindgen]
pub fn calculate_distance(p1: Point, p2: Point) -> f32 {
    let dx = p2.x - p1.x;
    let dy = p2.y - p1.y;
    (dx * dx + dy * dy).sqrt()
}

#[wasm_bindgen]
pub fn is_point_in_range(point: Point, center: Point, radius: f32) -> bool {
    calculate_distance(point, center) <= radius
} 