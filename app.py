from flask import Flask, render_template, request, redirect, url_for
from flask import flash
import sqlite3

app = Flask(__name__)
DB = "mtgr.db"
app.secret_key = "cetri_kresli"


def get_db_connection():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/sets")
def sets():
    conn = get_db_connection()
    sets = conn.execute("SELECT * FROM sets").fetchall()
    conn.close()
    return render_template("sets.html", sets=sets)


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404

@app.route("/sets/<int:set_id>")
def set_cards(set_id):

    conn = get_db_connection()

    set_info = conn.execute(
        "SELECT * FROM sets WHERE id = ?",
        (set_id,)
    ).fetchone()

    cards = conn.execute(
        "SELECT * FROM cards WHERE set_id = ?",
        (set_id,)
    ).fetchall()

    conn.close()

    return render_template(
        "cards.html",
        set=set_info,
        cards=cards
    )

@app.route("/card/<int:card_id>")
def card_detail(card_id):

    conn = get_db_connection()

    card = conn.execute(
        """
        SELECT cards.*, sets.name AS set_name
FROM cards
LEFT JOIN sets ON cards.set_id = sets.id
WHERE cards.id = ?
        """,
        (card_id,)
    ).fetchone()

    abilities = conn.execute(
        """
        SELECT abilities.name
        FROM abilities
        JOIN card_abilities
        ON abilities.id = card_abilities.ability_id
        WHERE card_abilities.card_id = ?
        """,
        (card_id,)
    ).fetchall()

    formats = conn.execute(
        """
        SELECT formats.name
        FROM formats
        JOIN card_formats
        ON formats.id = card_formats.format_id
        WHERE card_formats.card_id = ?
        """,
        (card_id,)
    ).fetchall()

    conn.close()

    return render_template(
        "card_detail.html",
        card=card,
        abilities=abilities,
        formats=formats
    )

@app.route("/debug")
def debug():
    conn = get_db_connection()

    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table';"
    ).fetchall()

    conn.close()

    return "<br>".join([table["name"] for table in tables])

@app.route("/cards/add", methods=["GET", "POST"])
def add_card():

    conn = get_db_connection()

    sets = conn.execute(
        "SELECT * FROM sets"
    ).fetchall()

    abilities = conn.execute(
        "SELECT * FROM abilities"
    ).fetchall()

    formats = conn.execute(
        "SELECT * FROM formats"
    ).fetchall()

    if request.method == "POST":

        name = request.form["name"]
        mana_cost = request.form["mana_cost"]
        colors = request.form["colors"]
        card_type = request.form["type"]
        power = request.form["power"]
        toughness = request.form["toughness"]
        description = request.form["description"]
        image = request.form["image"]
        set_id = request.form["set_id"]

        cursor = conn.execute(
            """
            INSERT INTO cards
            (
                name,
                mana_cost,
                colors,
                type,
                power,
                toughness,
                description,
                image,
                set_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                mana_cost,
                colors,
                card_type,
                power,
                toughness,
                description,
                image,
                set_id
            )
        )

        card_id = cursor.lastrowid

        selected_abilities = request.form.getlist("abilities")

        for ability_id in selected_abilities:

            conn.execute(
                """
                INSERT INTO card_abilities
                (card_id, ability_id)
                VALUES (?, ?)
                """,
                (card_id, ability_id)
            )

        selected_formats = request.form.getlist("formats")

        for format_id in selected_formats:

            conn.execute(
                """
                INSERT INTO card_formats
                (card_id, format_id)
                VALUES (?, ?)
                """,
                (card_id, format_id)
            )

        conn.commit()
        conn.close()

        flash("Card added successfully!")

        return redirect(url_for("cards"))

    conn.close()

    return render_template(
        "form.html",
        sets=sets,
        abilities=abilities,
        formats=formats
    )

@app.route("/cards")
def cards():

    color = request.args.get("color")
    type_search = request.args.get("type")

    conn = get_db_connection()

    query = "SELECT * FROM cards WHERE 1=1"
    params = []

    # COLOR FILTER
    if color:
        query += " AND colors LIKE ?"
        params.append(f"%{color}%")

    # TYPE SEARCH (free text)
    if type_search:
        query += " AND type LIKE ?"
        params.append(f"%{type_search}%")

    cards = conn.execute(query, params).fetchall()

    conn.close()

    return render_template("all_cards.html", cards=cards)


@app.route("/cards/edit/<int:card_id>", methods=["GET", "POST"])
def edit_card(card_id):

    conn = get_db_connection()

    card = conn.execute(
        "SELECT * FROM cards WHERE id = ?",
        (card_id,)
    ).fetchone()

    sets = conn.execute(
        "SELECT * FROM sets"
    ).fetchall()

    abilities = conn.execute(
        "SELECT * FROM abilities"
    ).fetchall()

    formats = conn.execute(
        "SELECT * FROM formats"
    ).fetchall()

    selected_abilities = conn.execute(
        """
        SELECT ability_id
        FROM card_abilities
        WHERE card_id = ?
        """,
        (card_id,)
    ).fetchall()

    selected_formats = conn.execute(
        """
        SELECT format_id
        FROM card_formats
        WHERE card_id = ?
        """,
        (card_id,)
    ).fetchall()

    selected_abilities = [
        row["ability_id"]
        for row in selected_abilities
    ]

    selected_formats = [
        row["format_id"]
        for row in selected_formats
    ]

    if request.method == "POST":

        conn.execute(
            """
            UPDATE cards
            SET
                name = ?,
                mana_cost = ?,
                colors = ?,
                type = ?,
                power = ?,
                toughness = ?,
                description = ?,
                image = ?,
                set_id = ?
            WHERE id = ?
            """,
            (
                request.form["name"],
                request.form["mana_cost"],
                request.form["colors"],
                request.form["type"],
                request.form["power"],
                request.form["toughness"],
                request.form["description"],
                request.form["image"],
                request.form["set_id"],
                card_id
            )
        )

        # REMOVE OLD LINKS
        conn.execute(
            "DELETE FROM card_abilities WHERE card_id = ?",
            (card_id,)
        )

        conn.execute(
            "DELETE FROM card_formats WHERE card_id = ?",
            (card_id,)
        )

        # REINSERT ABILITIES
        for ability_id in request.form.getlist("abilities"):

            conn.execute(
                """
                INSERT INTO card_abilities
                (card_id, ability_id)
                VALUES (?, ?)
                """,
                (card_id, ability_id)
            )

        # REINSERT FORMATS
        for format_id in request.form.getlist("formats"):

            conn.execute(
                """
                INSERT INTO card_formats
                (card_id, format_id)
                VALUES (?, ?)
                """,
                (card_id, format_id)
            )

        conn.commit()
        conn.close()

        flash("Card updated successfully!")

        return redirect(url_for(
            "card_detail",
            card_id=card_id
        ))

    conn.close()

    return render_template(
        "edit_card.html",
        card=card,
        sets=sets,
        abilities=abilities,
        formats=formats,
        selected_abilities=selected_abilities,
        selected_formats=selected_formats
    )

@app.route("/cards/delete/<int:card_id>", methods=["GET", "POST"])
def delete_card(card_id):

    conn = get_db_connection()

    card = conn.execute(
        "SELECT * FROM cards WHERE id = ?",
        (card_id,)
    ).fetchone()

    if request.method == "POST":

        conn.execute(
            "DELETE FROM card_abilities WHERE card_id = ?",
            (card_id,)
        )

        conn.execute(
            "DELETE FROM card_formats WHERE card_id = ?",
            (card_id,)
        )

        conn.execute(
            "DELETE FROM cards WHERE id = ?",
            (card_id,)
        )

        conn.commit()
        conn.close()

        flash("Card deleted successfully!")

        return redirect(url_for("cards"))

    conn.close()

    return render_template(
        "confirm_delete.html",
        card=card
    )

@app.route("/abilities")
def abilities():

    conn = get_db_connection()

    abilities = conn.execute(
        "SELECT * FROM abilities"
    ).fetchall()

    conn.close()

    return render_template(
        "abilities.html",
        abilities=abilities
    )

@app.route("/abilities/add", methods=["GET", "POST"])
def add_ability():

    conn = get_db_connection()

    if request.method == "POST":

        conn.execute(
            """
            INSERT INTO abilities
            (name, description)
            VALUES (?, ?)
            """,
            (
                request.form["name"],
                request.form["description"]
            )
        )

        conn.commit()
        conn.close()

        flash("Ability added successfully!")

        return redirect(url_for("abilities"))

    conn.close()

    return render_template(
        "ability_form.html",
        ability=None
    )

@app.route("/abilities/edit/<int:ability_id>", methods=["GET", "POST"])
def edit_ability(ability_id):

    conn = get_db_connection()

    ability = conn.execute(
        "SELECT * FROM abilities WHERE id = ?",
        (ability_id,)
    ).fetchone()

    if request.method == "POST":

        conn.execute(
            """
            UPDATE abilities
            SET
                name = ?,
                description = ?
            WHERE id = ?
            """,
            (
                request.form["name"],
                request.form["description"],
                ability_id
            )
        )

        conn.commit()
        conn.close()

        flash("Ability updated successfully!")

        return redirect(url_for("abilities"))

    conn.close()

    return render_template(
        "ability_form.html",
        ability=ability
    )

@app.route("/abilities/delete/<int:ability_id>", methods=["GET", "POST"])
def delete_ability(ability_id):

    conn = get_db_connection()

    ability = conn.execute(
        "SELECT * FROM abilities WHERE id = ?",
        (ability_id,)
    ).fetchone()

    if request.method == "POST":

        conn.execute(
            """
            DELETE FROM card_abilities
            WHERE ability_id = ?
            """,
            (ability_id,)
        )

        conn.execute(
            """
            DELETE FROM abilities
            WHERE id = ?
            """,
            (ability_id,)
        )

        conn.commit()
        conn.close()

        flash("Ability deleted successfully!")

        return redirect(url_for("abilities"))

    conn.close()

    return render_template(
        "confirm_delete_ability.html",
        ability=ability
    )
    

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/sets/add", methods=["GET", "POST"])
def add_set():

    conn = get_db_connection()

    if request.method == "POST":

        conn.execute(
    """
    INSERT INTO sets
    (
        name,
        description,
        release_year,
        image,
        image_type
    )
    VALUES (?, ?, ?, ?, ?)
    """,
    (
        request.form["name"],
        request.form["description"],
        request.form["release_year"],
        request.form["image"],
        request.form["image_type"]
    )
)
        conn.commit()
        conn.close()

        flash("Set added successfully!")

        return redirect(url_for("sets"))

    conn.close()

    return render_template(
        "set_form.html",
        set=None
    )


@app.route("/sets/edit/<int:set_id>", methods=["GET", "POST"])
def edit_set(set_id):

    conn = get_db_connection()

    set_item = conn.execute(
        "SELECT * FROM sets WHERE id = ?",
        (set_id,)
    ).fetchone()

    if request.method == "POST":

        conn.execute(
    """
    UPDATE sets
    SET
        name = ?,
        description = ?,
        release_year = ?,
        image = ?,
        image_type = ?
    WHERE id = ?
    """,
    (
        request.form["name"],
        request.form["description"],
        request.form["release_year"],
        request.form["image"],
        request.form["image_type"],
        set_id
    )
)
        conn.commit()
        conn.close()

        flash("Set updated successfully!")

        return redirect(url_for("sets"))

    conn.close()

    return render_template(
        "set_form.html",
        set=set_item
    )

@app.route("/sets/delete/<int:set_id>", methods=["GET", "POST"])
def delete_set(set_id):

    conn = get_db_connection()

    set_item = conn.execute(
        "SELECT * FROM sets WHERE id = ?",
        (set_id,)
    ).fetchone()

    if request.method == "POST":

        conn.execute(
            """
            UPDATE cards
            SET set_id = NULL
            WHERE set_id = ?
            """,
            (set_id,)
        )

        conn.execute(
            "DELETE FROM sets WHERE id = ?",
            (set_id,)
        )

        conn.commit()
        conn.close()

        flash("Set deleted successfully!")

        return redirect(url_for("sets"))

    conn.close()

    return render_template(
        "confirm_delete_set.html",
        set=set_item
    )


"""eksperimenti baigie"""



if __name__ == "__main__":
    app.run(debug=True)