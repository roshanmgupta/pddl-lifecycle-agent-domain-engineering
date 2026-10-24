(define (domain woodworking08)
  (:requirements :strips :typing)
  (:types
    object - any
    acolour awood woodobj machine surface treatmentstatus aboardsize apartsize - object
    highspeed-saw glazer grinder immersion-varnisher planer saw spray-varnisher - machine
    board part - woodobj
  )
  (:predicates
    (available ?x - woodobj)
    (unused ?x - part)
    (has_colour ?m - machine ?c - acolour)
    (surface_condition ?x - woodobj ?s - surface)
    (undergoing_treatment ?x - woodobj ?t - treatmentstatus)
    (colour ?x - woodobj ?c - acolour)
    (made_of ?x - woodobj ?w - awood)
    (size ?x - woodobj ?s - aboardsize)
    (goal_size ?x - part ?s - apartsize)
    (empty ?m - highspeed-saw)
    (in_highspeed_saw ?x - board ?m - highspeed-saw)
    (successor ?s1 ?s2 - aboardsize)
    (grind_treatment_change ?t1 ?t2 - treatmentstatus)
    (is_smooth ?s - surface)
  )
  (:action do_immersion_varnish
    :parameters (?p - part ?v - immersion-varnisher ?c - acolour ?s - surface)
    :precondition (and (available ?p) (has_colour ?v ?c) (surface_condition ?p ?s) (is_smooth ?s) (undergoing_treatment ?p untreated))
    :effect (and (undergoing_treatment ?p varnished) (colour ?p ?c) (not (undergoing_treatment ?p untreated)) (not (colour ?p natural)))
  )
  (:action do_spray_varnish
    :parameters (?p - part ?v - spray-varnisher ?c - acolour ?s - surface)
    :precondition (and (available ?p) (has_colour ?v ?c) (surface_condition ?p ?s) (is_smooth ?s) (undergoing_treatment ?p untreated))
    :effect (and (undergoing_treatment ?p varnished) (colour ?p ?c) (not (undergoing_treatment ?p untreated)) (not (colour ?p natural)))
  )
  (:action do_glaze
    :parameters (?p - part ?g - glazer ?c - acolour)
    :precondition (and (available ?p) (has_colour ?g ?c) (undergoing_treatment ?p untreated))
    :effect (and (undergoing_treatment ?p glazed) (colour ?p ?c) (not (undergoing_treatment ?p untreated)) (not (colour ?p natural)))
  )
  (:action do_grind
    :parameters (?p - part ?g - grinder ?s1 ?s2 - surface ?c1 ?c2 - acolour ?t1 ?t2 - treatmentstatus)
    :precondition (and (available ?p) (surface_condition ?p ?s1) (is_smooth ?s1) (colour ?p ?c1) (undergoing_treatment ?p ?t1) (grind_treatment_change ?t1 ?t2))
    :effect (and (surface_condition ?p ?s2) (undergoing_treatment ?p ?t2) (colour ?p natural) (not (surface_condition ?p ?s1)) (not (undergoing_treatment ?p ?t1)) (not (colour ?p ?c1)))
  )
  (:action do_plane
    :parameters (?p - part ?pl - planer ?s1 ?s2 - surface ?c1 ?c2 - acolour ?t1 ?t2 - treatmentstatus)
    :precondition (and (available ?p) (surface_condition ?p ?s1) (undergoing_treatment ?p ?t1) (colour ?p ?c1))
    :effect (and (surface_condition ?p ?s2) (undergoing_treatment ?p ?t2) (colour ?p natural) (not (surface_condition ?p ?s1)) (not (undergoing_treatment ?p ?t1)) (not (colour ?p ?c1)))
  )
  (:action load_board
    :parameters (?b - board ?h - highspeed-saw)
    :precondition (and (empty ?h) (available ?b))
    :effect (and (in_highspeed_saw ?b ?h) (not (available ?b)) (not (empty ?h)))
  )
  (:action unload_board
    :parameters (?b - board ?h - highspeed-saw)
    :precondition (in_highspeed_saw ?b ?h)
    :effect (and (available ?b) (empty ?h) (not (in_highspeed_saw ?b ?h)))
  )
  (:action cut_board_small
    :parameters (?b - board ?p - part ?h - highspeed-saw ?w - awood ?s - surface ?s1 ?s2 - aboardsize)
    :precondition (and (unused ?p) (goal_size ?p small) (in_highspeed_saw ?b ?h) (made_of ?b ?w) (surface_condition ?b ?s) (size ?b ?s1) (successor ?s1 ?s2))
    :effect (and (available ?p) (made_of ?p ?w) (surface_condition ?p ?s) (colour ?p natural) (undergoing_treatment ?p untreated) (size ?b ?s2) (not (unused ?p)))
  )
  (:action cut_board_medium
    :parameters (?b - board ?p - part ?h - highspeed-saw ?w - awood ?s - surface ?s1 ?s2 ?s3 - aboardsize)
    :precondition (and (unused ?p) (goal_size ?p medium) (in_highspeed_saw ?b ?h) (made_of ?b ?w) (surface_condition ?b ?s) (size ?b ?s1) (successor ?s2 ?s3) (successor ?s1 ?s2))
    :effect (and (available ?p) (made_of ?p ?w) (surface_condition ?p ?s) (colour ?p natural) (undergoing_treatment ?p untreated) (size ?b ?s3) (not (unused ?p)))
  )
  (:action cut_board_large
    :parameters (?b - board ?p - part ?h - highspeed-saw ?w - awood ?s - surface ?s1 ?s2 ?s3 ?s4 - aboardsize)
    :precondition (and (unused ?p) (goal_size ?p large) (in_highspeed_saw ?b ?h) (made_of ?b ?w) (surface_condition ?b ?s) (size ?b ?s1) (successor ?s3 ?s4) (successor ?s2 ?s3) (successor ?s1 ?s2))
    :effect (and (available ?p) (made_of ?p ?w) (surface_condition ?p ?s) (colour ?p natural) (undergoing_treatment ?p untreated) (size ?b ?s4) (not (unused ?p)))
  )
  (:action saw_board_small
    :parameters (?b - board ?p - part ?s - saw ?w - awood ?s1 ?s2 - aboardsize)
    :precondition (and (unused ?p) (goal_size ?p small) (available ?b) (made_of ?b ?w) (surface_condition ?b ?s1) (size ?b ?s1) (successor ?s1 ?s2))
    :effect (and (available ?p) (made_of ?p ?w) (surface_condition ?p ?s1) (colour ?p natural) (undergoing_treatment ?p untreated) (size ?b ?s2) (not (unused ?p)))
  )
  (:action saw_board_medium
    :parameters (?b - board ?p - part ?s - saw ?w - awood ?s1 ?s2 ?s3 - aboardsize)
    :precondition (and (unused ?p) (goal_size ?p medium) (available ?b) (made_of ?b ?w) (surface_condition ?b ?s1) (size ?b ?s1) (successor ?s2 ?s3) (successor ?s1 ?s2))
    :effect (and (available ?p) (made_of ?p ?w) (surface_condition ?p ?s1) (colour ?p natural) (undergoing_treatment ?p untreated) (size ?b ?s3) (not (unused ?p)))
  )
  (:action saw_board_large
    :parameters (?b - board ?p - part ?s - saw ?w - awood ?s1 ?s2 ?s3 ?s4 - aboardsize)
    :precondition (and (unused ?p) (goal_size ?p large) (available ?b) (made_of ?b ?w) (surface_condition ?b ?s1) (size ?b ?s1) (successor ?s3 ?s4) (successor ?s2 ?s3) (successor ?s1 ?s2))
    :effect (and (available ?p) (made_of ?p ?w) (surface_condition ?p ?s1) (colour ?p natural) (undergoing_treatment ?p untreated) (size ?b ?s4) (not (unused ?p)))
  )
)