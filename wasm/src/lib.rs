use wasm_bindgen::prelude::*;
use std::f32;

#[wasm_bindgen]
pub struct Point {
    x: f32,
    y: f32,
    score: f32,
}

#[wasm_bindgen]
impl Point {
    #[wasm_bindgen(constructor)]
    pub fn new(x: f32, y: f32, score: f32) -> Point {
        Point { x, y, score }
    }
}

#[wasm_bindgen]
pub fn calculate_angles(points: &[f32]) -> Vec<f32> {
    let mut result = Vec::new();
    let point_count = points.len() / 3;
    
    for i in 0..point_count - 2 {
        let p1 = Point::new(
            points[i * 3],
            points[i * 3 + 1],
            points[i * 3 + 2]
        );
        let p2 = Point::new(
            points[(i + 1) * 3],
            points[(i + 1) * 3 + 1],
            points[(i + 1) * 3 + 2]
        );
        let p3 = Point::new(
            points[(i + 2) * 3],
            points[(i + 2) * 3 + 1],
            points[(i + 2) * 3 + 2]
        );
        
        let (angle, confidence, is_correct) = calculate_angle(&p1, &p2, &p3);
        result.push(angle);
        result.push(confidence);
        result.push(if is_correct { 1.0 } else { 0.0 });
    }
    
    result
}

#[wasm_bindgen]
pub fn calculate_velocities(current: &[f32], previous: &[f32]) -> Vec<f32> {
    let mut velocities = Vec::new();
    let point_count = current.len() / 3;
    
    for i in 0..point_count {
        let curr_x = current[i * 3];
        let curr_y = current[i * 3 + 1];
        let curr_score = current[i * 3 + 2];
        
        let prev_x = previous[i * 3];
        let prev_y = previous[i * 3 + 1];
        let prev_score = previous[i * 3 + 2];
        
        if curr_score > 0.3 && prev_score > 0.3 {
            let dx = curr_x - prev_x;
            let dy = curr_y - prev_y;
            velocities.push((dx * dx + dy * dy).sqrt());
        } else {
            velocities.push(0.0);
        }
    }
    
    velocities
}

#[wasm_bindgen]
pub fn calculate_confidence(scores: &[f32]) -> f32 {
    let valid_count = scores.iter()
        .filter(|&&score| score > 0.3)
        .count();
    
    valid_count as f32 / scores.len() as f32
}

fn calculate_angle(p1: &Point, p2: &Point, p3: &Point) -> (f32, f32, bool) {
    if p1.score < 0.3 || p2.score < 0.3 || p3.score < 0.3 {
        return (0.0, 0.0, false);
    }
    
    let confidence = p1.score.min(p2.score).min(p3.score);
    
    let v1_x = p2.x - p1.x;
    let v1_y = p2.y - p1.y;
    let v2_x = p3.x - p2.x;
    let v2_y = p3.y - p2.y;
    
    let dot = v1_x * v2_x + v1_y * v2_y;
    let cross = v1_x * v2_y - v1_y * v2_x;
    
    let angle = cross.atan2(dot).abs() * 180.0 / std::f32::consts::PI;
    let is_correct = true; // This should be determined by exercise-specific logic
    
    (angle, confidence, is_correct)
} 