from sqlalchemy import text

PEOPLE_INSERT_QUERY = text(
    """ 
        INSERT INTO people
        (execution_id, simulation_id, cycle, started_from_cycle, name, id, date_of_birth, objective, speed, state, living_place, working_place, start_work_h, end_work_h, x, y)
        VALUES
        (:execution_id, :simulation_id, :cycle, :started_from_cycle, :name, :id, :date_of_birth, :objective, :speed, :state, :living_place, :working_place, :start_work_h, :end_work_h, :x, :y)
    """
)

MOSQUITOES_INSERT_QUERY = text(
    """ 
        INSERT INTO mosquitoes
        (execution_id, simulation_id, cycle, started_from_cycle, name, id, date_of_birth, speed, state, curr_building, bs_id, x, y)
        VALUES
        (:execution_id, :simulation_id, :cycle, :started_from_cycle, :name, :id, :date_of_birth, :speed, :state, :curr_building, :bs_id, :x, :y)
    """
)

BREEDING_SITES_INSERT_QUERY = text(
    """ 
        INSERT INTO breeding_sites
        (execution_id, simulation_id, cycle, started_from_cycle, name, id, date_of_birth, active, eggs, curr_building, x, y)
        VALUES
        (:execution_id, :simulation_id, :cycle, :started_from_cycle, :name, :id, :date_of_birth, :active, :eggs, :curr_building, :x, :y)
    """
)

NOTIFICATIONS_BETWEEN_DATES_QUERY = text(
    """
        SELECT * FROM cases
        WHERE city = :city
            AND data_notification BETWEEN :start_date AND :end_date
    """
)
