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
    colourfragments - object
  )

  (:init
    (is-successor s0 s1)
    (is-successor s1 s2)
    (is-successor s2 s3)
    (has-colour glazer0 mauve)
    (has-colour glazer0 green)
    (has-colour immersion-varnisher0 mauve)
    (is-empty highspeed-saw0)
    (has-colour spray-varnisher0 mauve)
    (is-unused p0)
    (is-successor p0 medium)
    (is-unused p1)
    (is-successor p1 medium)
    (is-available p2)
    (has-colour p2 natural)
    (has-wood p2 beech)
    (has-surface p2 verysmooth)
    (is-undergoing p2 colourfragments)
    (is-successor p2 small)
    (has-wood b0 beech)
    (has-surface b0 rough)
    (is-available b0)
    (is-successor b0 s3)
    (has-wood b1 cherry)
    (has-surface b1 rough)
    (is-available b1)
  )

  (:goal (and (is-available p0) (has-colour p0 mauve) (has-wood p0 beech) (has-surface p0 verysmooth) (is-undergoing p0 varnished) (is-available p1) (has-colour p1 green) (has-wood p1 cherry) (has-surface p1 smooth) (is-undergoing p1 glazed) (is-available p2) (has-colour p2 mauve) (has-wood p2 beech)))
)