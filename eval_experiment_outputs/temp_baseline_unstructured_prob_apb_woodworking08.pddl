(define (problem instance-1)
  (:domain woodworking08)
  (:objects
    grinder0 - grinder
    glazer0 - glazer
    immersion-varnisher0 - immersion-varnisher
    planer0 - planer
    highspeed-saw0 - highspeed-saw
    spray-varnisher0 - spray-varnisher
    saw0 - saw
    green mauve - acolour
    cherry beech - awood
    p0 p1 p2 - part
    b0 b1 - board
    s0 s1 s2 s3 - aboardsize
  )
  (:init
    (grind_treatment_change varnished colourfragments)
    (grind_treatment_change glazed untreated)
    (grind_treatment_change untreated untreated)
    (grind_treatment_change colourfragments untreated)
    (is_smooth smooth)
    (is_smooth verysmooth)
    (successor s0 s1)
    (successor s1 s2)
    (successor s2 s3)
    (has_colour glazer0 mauve)
    (has_colour glazer0 green)
    (has_colour immersion-varnisher0 mauve)
    (empty highspeed-saw0)
    (has_colour spray-varnisher0 mauve)
    (unused p0)
    (goal_size p0 medium)
    (unused p1)
    (goal_size p1 medium)
    (available p2)
    (colour p2 natural)
    (made_of p2 beech)
    (surface_condition p2 verysmooth)
    (undergoing_treatment p2 colourfragments)
    (goal_size p2 small)
    (size b0 s3)
    (made_of b0 beech)
    (surface_condition b0 rough)
    (available b0)
    (size b1 s3)
    (made_of b1 cherry)
    (surface_condition b1 rough)
    (available b1)
  )
  (:goal
    (and
      (available p0)
      (colour p0 mauve)
      (made_of p0 beech)
      (surface_condition p0 verysmooth)
      (undergoing_treatment p0 varnished)
      (available p1)
      (colour p1 green)
      (made_of p1 cherry)
      (surface_condition p1 smooth)
      (undergoing_treatment p1 glazed)
      (available p2)
      (colour p2 mauve)
      (made_of p2 beech)
    )
  )
)