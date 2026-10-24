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
    colourfragments untreated medium small verysmooth rough varnished smooth glazed - object
  )

  (:init
    (is-undergoing-treatment p2 colourfragments)
    (is-undergoing-treatment glazer0 untreated)
    (is-undergoing-treatment immersion-varnisher0 untreated)
    (is-undergoing-treatment spray-varnisher0 untreated)
    (is-available b0)
    (is-available b1)
    (has-colour glazer0 mauve)
    (has-colour glazer0 green)
    (has-colour immersion-varnisher0 mauve)
    (is-empty highspeed-saw0)
    (is-unused p0)
    (goal-size p0 medium)
    (is-unused p1)
    (goal-size p1 medium)
    (is-available p2)
    (is-undergoing-treatment p2 colourfragments)
    (goal-size p2 small)
    (is-made-of p2 beech)
    (has-surface-condition p2 verysmooth)
    (is-available b0)
    (is-made-of b0 beech)
    (has-surface-condition b0 rough)
    (successor s0 s1)
    (successor s1 s2)
    (successor s2 s3)
    (is-available b1)
    (is-made-of b1 cherry)
    (has-surface-condition b1 rough)
  )

  (:goal (and (is-available p0) (has-colour p0 mauve) (is-made-of p0 beech) (has-surface-condition p0 verysmooth) (is-undergoing-treatment p0 varnished) (is-available p1) (has-colour p1 green) (is-made-of p1 cherry) (has-surface-condition p1 smooth) (is-undergoing-treatment p1 glazed) (is-available p2) (has-colour p2 mauve) (is-made-of p2 beech)))
)