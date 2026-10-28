(define (domain pegsolitaire-sequential)
    (:requirements :strips :typing)
    (:types location)
    (:predicates 
        (free ?l - location)
        (occupied ?l - location)
        (IN-LINE ?l1 ?l2 ?l3 - location)
        (move-ended)
        (last-visited ?l - location)
    )
    
    (:action jump-new-move
        :parameters (?A ?B ?C - location)
        :precondition (and 
            (move-ended)
            (IN-LINE ?A ?B ?C)
            (occupied ?A)
            (occupied ?B)
            (free ?C)
        )
        :effect (and 
            (not (move-ended))
            (not (occupied ?A))
            (not (occupied ?B))
            (occupied ?C)
            (last-visited ?C)
            (free ?A)
            (free ?B)
            (not (free ?C))
        )
    )
    
    (:action continue-jump
        :parameters (?A ?B ?C - location)
        :precondition (and 
            (last-visited ?A)
            (IN-LINE ?A ?B ?C)
            (occupied ?A)
            (occupied ?B)
            (free ?C)
        )
        :effect (and 
            (not (occupied ?A))
            (not (occupied ?B))
            (occupied ?C)
            (last-visited ?C)
            (free ?A)
            (free ?B)
            (not (free ?C))
            (not (last-visited ?A))
        )
    )
    
    (:action end-move
        :parameters (?A - location)
        :precondition (and 
            (last-visited ?A)
        )
        :effect (and 
            (move-ended)
            (not (last-visited ?A))
        )
    )
)