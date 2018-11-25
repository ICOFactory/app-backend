CREATE TABLE charting_cache
(
    id int unsigned PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(45),
    value LONGBLOB,
    updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);