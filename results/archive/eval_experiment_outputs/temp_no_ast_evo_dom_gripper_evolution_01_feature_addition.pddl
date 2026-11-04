(define (domain gripper-strips)
 (:requirements :strips :typing) 
 (:types room object robot gripper)
 (:predicates (at-robby ?r - robot ?x - room)
 	      (at ?o - object ?x - room)
	      (free ?r - robot ?g - gripper)
	      (carry ?r - robot ?o - object ?g - gripper))

   (:action move
       :parameters  (?r - robot ?from ?to - room)
       :precondition (and  (at-robby ?r ?from))
       :effect (and  (at-robby ?r ?to)
		     (not (at-robby ?r ?from))))

   (:action pick
       :parameters (?r - robot ?obj - object ?room - room ?g - gripper)
       :precondition  (and  (at ?obj ?room) (at-robby ?r ?room) (free ?r ?g))
       :effect (and (carry ?r ?obj ?g)
		    (not (at ?obj ?room)) 
		    (not (free ?r ?g))))

   (:action drop
       :parameters (?r - robot ?obj - object ?room - room ?g - gripper)
       :precondition  (and  (carry ?r ?obj ?g) (at-robby ?r ?room))
       :effect (and (at ?obj ?room)
		    (free ?r ?g)
		    (not (carry ?r ?obj ?g))))

   (:action cooperative-transfer
       :parameters (?a ?b - robot ?c - object ?d ?e - gripper ?f - room)
       :precondition (and (at-robby ?a ?f)
                          (at-robby ?b ?f)
                          (carry ?a ?c ?d)
                          (free ?b ?e))
       :effect (and (carry ?b ?c ?e)
                    (free ?a ?d)
                    (not (carry ?a ?c ?d))
                    (not (free ?b ?e)))))