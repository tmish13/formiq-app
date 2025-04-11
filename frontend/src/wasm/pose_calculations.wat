(module
  (import "env" "memory" (memory 1))
  (import "env" "memoryBase" (global $memoryBase i32))
  (import "env" "tableBase" (global $tableBase i32))
  (import "env" "_abs" (func $abs (param f64) (result f64)))
  (import "env" "_cos" (func $cos (param f64) (result f64)))
  (import "env" "_sin" (func $sin (param f64) (result f64)))
  (import "env" "_atan2" (func $atan2 (param f64 f64) (result f64)))
  (import "env" "_sqrt" (func $sqrt (param f64) (result f64)))

  ;; Helper function to calculate angle between three points
  (func $calculate_angle (param $x1 f64) (param $y1 f64) (param $x2 f64) (param $y2 f64) (param $x3 f64) (param $y3 f64) (result f64)
    (local $v1x f64)
    (local $v1y f64)
    (local $v2x f64)
    (local $v2y f64)
    (local $dot_product f64)
    (local $v1_mag f64)
    (local $v2_mag f64)
    (local $cos_angle f64)
    (local $angle f64)

    ;; Calculate vectors
    (set_local $v1x (f64.sub (get_local $x1) (get_local $x2)))
    (set_local $v1y (f64.sub (get_local $y1) (get_local $y2)))
    (set_local $v2x (f64.sub (get_local $x3) (get_local $x2)))
    (set_local $v2y (f64.sub (get_local $y3) (get_local $y2)))

    ;; Calculate dot product
    (set_local $dot_product 
      (f64.add 
        (f64.mul (get_local $v1x) (get_local $v2x))
        (f64.mul (get_local $v1y) (get_local $v2y))))

    ;; Calculate magnitudes
    (set_local $v1_mag 
      (call $sqrt 
        (f64.add 
          (f64.mul (get_local $v1x) (get_local $v1x))
          (f64.mul (get_local $v1y) (get_local $v1y)))))
    
    (set_local $v2_mag 
      (call $sqrt 
        (f64.add 
          (f64.mul (get_local $v2x) (get_local $v2x))
          (f64.mul (get_local $v2y) (get_local $v2y)))))

    ;; Calculate cos(angle)
    (set_local $cos_angle 
      (f64.div 
        (get_local $dot_product)
        (f64.mul (get_local $v1_mag) (get_local $v2_mag))))

    ;; Clamp cos_angle to [-1, 1] to avoid numerical errors
    (set_local $cos_angle 
      (f64.max 
        (f64.min (get_local $cos_angle) (f64.const 1.0))
        (f64.const -1.0)))

    ;; Calculate angle in radians
    (set_local $angle (call $acos (get_local $cos_angle)))

    ;; Convert to degrees
    (f64.mul (get_local $angle) (f64.const 180.0))
  )

  ;; Calculate angles for all keypoints
  (func $calculateAngles (param $points i32) (param $length i32) (result i32)
    (local $i i32)
    (local $angles i32)
    (local $x1 f64)
    (local $y1 f64)
    (local $x2 f64)
    (local $y2 f64)
    (local $x3 f64)
    (local $y3 f64)

    ;; Allocate memory for angles array
    (set_local $angles (call $malloc (i32.mul (get_local $length) (i32.const 8))))

    ;; Loop through points and calculate angles
    (set_local $i (i32.const 0))
    (loop $angleLoop
      (br_if $angleLoop (i32.ge_s (get_local $i) (get_local $length)))

      ;; Get point coordinates
      (set_local $x1 (f64.load (i32.add (get_local $points) (i32.mul (get_local $i) (i32.const 8)))))
      (set_local $y1 (f64.load (i32.add (get_local $points) (i32.add (i32.mul (get_local $i) (i32.const 8)) (i32.const 8)))))
      (set_local $x2 (f64.load (i32.add (get_local $points) (i32.mul (i32.add (get_local $i) (i32.const 1)) (i32.const 8)))))
      (set_local $y2 (f64.load (i32.add (get_local $points) (i32.add (i32.mul (i32.add (get_local $i) (i32.const 1)) (i32.const 8)) (i32.const 8)))))
      (set_local $x3 (f64.load (i32.add (get_local $points) (i32.mul (i32.add (get_local $i) (i32.const 2)) (i32.const 8)))))
      (set_local $y3 (f64.load (i32.add (get_local $points) (i32.add (i32.mul (i32.add (get_local $i) (i32.const 2)) (i32.const 8)) (i32.const 8)))))

      ;; Calculate and store angle
      (f64.store (i32.add (get_local $angles) (i32.mul (get_local $i) (i32.const 8)))
        (call $calculate_angle 
          (get_local $x1) (get_local $y1)
          (get_local $x2) (get_local $y2)
          (get_local $x3) (get_local $y3)))

      (set_local $i (i32.add (get_local $i) (i32.const 1)))
      (br $angleLoop)
    )

    (get_local $angles)
  )

  ;; Calculate velocities between current and previous points
  (func $calculateVelocities (param $current i32) (param $previous i32) (param $length i32) (result i32)
    (local $i i32)
    (local $velocities i32)
    (local $dx f64)
    (local $dy f64)

    ;; Allocate memory for velocities array
    (set_local $velocities (call $malloc (i32.mul (get_local $length) (i32.const 8))))

    ;; Loop through points and calculate velocities
    (set_local $i (i32.const 0))
    (loop $velocityLoop
      (br_if $velocityLoop (i32.ge_s (get_local $i) (get_local $length)))

      ;; Calculate velocity components
      (set_local $dx (f64.sub 
        (f64.load (i32.add (get_local $current) (i32.mul (get_local $i) (i32.const 8))))
        (f64.load (i32.add (get_local $previous) (i32.mul (get_local $i) (i32.const 8))))))
      (set_local $dy (f64.sub 
        (f64.load (i32.add (get_local $current) (i32.add (i32.mul (get_local $i) (i32.const 8)) (i32.const 8))))
        (f64.load (i32.add (get_local $previous) (i32.add (i32.mul (get_local $i) (i32.const 8)) (i32.const 8))))))

      ;; Store velocity magnitude
      (f64.store (i32.add (get_local $velocities) (i32.mul (get_local $i) (i32.const 8)))
        (call $sqrt (f64.add 
          (f64.mul (get_local $dx) (get_local $dx))
          (f64.mul (get_local $dy) (get_local $dy)))))

      (set_local $i (i32.add (get_local $i) (i32.const 1)))
      (br $velocityLoop)
    )

    (get_local $velocities)
  )

  ;; Calculate confidence score from keypoint scores
  (func $calculateConfidence (param $scores i32) (param $length i32) (result f64)
    (local $i i32)
    (local $sum f64)

    ;; Sum all scores
    (set_local $i (i32.const 0))
    (set_local $sum (f64.const 0.0))
    (loop $confidenceLoop
      (br_if $confidenceLoop (i32.ge_s (get_local $i) (get_local $length)))

      (set_local $sum (f64.add (get_local $sum) 
        (f64.load (i32.add (get_local $scores) (i32.mul (get_local $i) (i32.const 8))))))

      (set_local $i (i32.add (get_local $i) (i32.const 1)))
      (br $confidenceLoop)
    )

    ;; Return average confidence
    (f64.div (get_local $sum) (f64.convert_s/i32 (get_local $length)))
  )

  ;; Calculate center of mass from keypoints
  (func $calculateCenterOfMass (param $points i32) (param $length i32) (result i32)
    (local $i i32)
    (local $center i32)
    (local $sumX f64)
    (local $sumY f64)

    ;; Allocate memory for center point
    (set_local $center (call $malloc (i32.const 16)))

    ;; Calculate sum of coordinates
    (set_local $i (i32.const 0))
    (set_local $sumX (f64.const 0.0))
    (set_local $sumY (f64.const 0.0))
    (loop $centerLoop
      (br_if $centerLoop (i32.ge_s (get_local $i) (get_local $length)))

      (set_local $sumX (f64.add (get_local $sumX) 
        (f64.load (i32.add (get_local $points) (i32.mul (get_local $i) (i32.const 8))))))
      (set_local $sumY (f64.add (get_local $sumY) 
        (f64.load (i32.add (get_local $points) (i32.add (i32.mul (get_local $i) (i32.const 8)) (i32.const 8))))))

      (set_local $i (i32.add (get_local $i) (i32.const 1)))
      (br $centerLoop)
    )

    ;; Store center point coordinates
    (f64.store (get_local $center) 
      (f64.div (get_local $sumX) (f64.convert_s/i32 (get_local $length))))
    (f64.store (i32.add (get_local $center) (i32.const 8))
      (f64.div (get_local $sumY) (f64.convert_s/i32 (get_local $length))))

    (get_local $center)
  )

  ;; Memory management functions
  (func $malloc (param $size i32) (result i32)
    (local $ptr i32)
    (set_local $ptr (get_global $memoryBase))
    (set_global $memoryBase (i32.add (get_global $memoryBase) (get_local $size)))
    (get_local $ptr)
  )

  ;; Export functions
  (export "calculateAngles" (func $calculateAngles))
  (export "calculateVelocities" (func $calculateVelocities))
  (export "calculateConfidence" (func $calculateConfidence))
  (export "calculateCenterOfMass" (func $calculateCenterOfMass))
  (export "malloc" (func $malloc))
  (export "calculate_angle" (func $calculate_angle))
) 