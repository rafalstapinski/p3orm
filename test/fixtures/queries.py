BASE_TABLES = """
CREATE TABLE company (
    id SERIAL PRIMARY KEY,
    name text NOT NULL,
    created_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    different_column_name text
);


CREATE TABLE employee (
    id SERIAL PRIMARY KEY,
    name text NOT NULL,
    created_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    company_id bigint REFERENCES company(id)
);


CREATE TABLE org_chart (
    id SERIAL PRIMARY KEY,
    manager_id bigint NOT NULL REFERENCES employee(id),
    report_id bigint NOT NULL REFERENCES employee(id)
);
"""

BASE_DATA = """
INSERT INTO company (name, different_column_name) VALUES ('Company 1', 'yeet');
INSERT INTO company (name) VALUES ('Company 2');
INSERT INTO company (name) VALUES ('Company 3');
INSERT INTO company (name) VALUES ('Company 4');

INSERT INTO employee (name, company_id) VALUES ('Person 1', 1);
INSERT INTO employee (name, company_id) VALUES ('Person 2', 1);
INSERT INTO employee (name, company_id) VALUES ('Person 3', 1);
INSERT INTO employee (name, company_id) VALUES ('Person 4', 1);
INSERT INTO employee (name, company_id) VALUES ('Person 5', 1);
INSERT INTO employee (name, company_id) VALUES ('Person 6', null);

INSERT INTO org_chart (manager_id, report_id) VALUES (1, 2);
INSERT INTO org_chart (manager_id, report_id) VALUES (1, 3);
INSERT INTO org_chart (manager_id, report_id) VALUES (3, 4);
INSERT INTO org_chart (manager_id, report_id) VALUES (3, 5);
"""
