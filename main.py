from flask import Flask, render_template, request, url_for, redirect, flash
import psycopg2
import os
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your_default_secret_key')

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# PostgreSQL Connection Details - from environment variable
string_de_conexao = os.environ.get("DATABASE_URL", "postgresql://banco_teste01_user:mAsurw0iY63x7nfhJw3d3MJZzte3860L@dpg-d0ocenre5dus73auodk0-a.oregon-postgres.render.com/banco_teste01")
nome_da_tabela = "banco_teste01" # New Table Name

def get_db_connection():
    """Establish a PostgreSQL database connection."""
    try:
        conn = psycopg2.connect(string_de_conexao)
        return conn
    except psycopg2.Error as err:
        logging.error(f"Database connection failed: {err}")
        flash(f"Erro ao conectar ao banco de dados: {err}", 'error')  # Use Flask's flash
        return None

def close_db_connection(conn):
    """Close a database connection."""
    if conn:
        conn.close()
        logging.info("Database connection closed")

def adicionar_colunas_se_nao_existirem():
    """Adds required columns to the 'banco_teste01' table if they don't exist."""
    conn = get_db_connection()
    if not conn:
        return

    try:
        with conn.cursor() as cursor:
            # Check if the columns already exist using information_schema.columns
            cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{nome_da_tabela}' AND column_name = 'a_atendimento'")
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE {nome_da_tabela} ADD COLUMN a_atendimento VARCHAR(255) NULL")
                logging.info("Coluna 'a_atendimento' adicionada.")

            cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{nome_da_tabela}' AND column_name = 'a_pizzas'")
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE {nome_da_tabela} ADD COLUMN a_pizzas VARCHAR(255) NULL")
                logging.info("Coluna 'a_pizzas' adicionada.")

            cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{nome_da_tabela}' AND column_name = 'a_entregas'")
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE {nome_da_tabela} ADD COLUMN a_entregas VARCHAR(255) NULL")
                logging.info("Coluna 'a_entregas' adicionada.")

            cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{nome_da_tabela}' AND column_name = 'media'")
            if not cursor.fetchone():
                cursor.execute(f"ALTER TABLE {nome_da_tabela} ADD COLUMN media DECIMAL(10,2) NULL")
                logging.info("Coluna 'media' adicionada.")

            conn.commit() # Commit the changes

    except psycopg2.Error as err:
        logging.error(f"Erro ao adicionar colunas: {err}")
        flash(f"Erro ao adicionar colunas: {err}", 'error')

    finally:
        close_db_connection(conn)

# Run column addition during application startup
with app.app_context():
    adicionar_colunas_se_nao_existirem()

@app.route('/', methods=['GET', 'POST'])
def index():
    mensagem = None
    media_geral = None

    if request.method == 'POST':
        nome = request.form.get('nome')
        telefone = request.form.get('telefone')
        observacoes = request.form.get('mensagem')
        a_atendimento = request.form.get('avaliacao_atendimento')
        a_pizzas = request.form.get('avaliacao_pizza')
        a_entregas = request.form.get('avaliacao_entrega')
        media = request.form.get('avaliacao_geral')

        if not all([nome, telefone, a_atendimento, a_pizzas, a_entregas, media]):
            flash("Por favor, preencha todos os campos obrigatórios.", 'warning')
            return render_template('index.html', mensagem=mensagem, media_geral=media_geral)

        conn = get_db_connection()
        if not conn:
            return render_template('index.html', mensagem=mensagem, media_geral=media_geral)

        try:
            with conn.cursor() as cursor:
                query = f"INSERT INTO {nome_da_tabela} (pessoas, numero_telefone, observacoes, a_atendimento, a_pizzas, a_entregas, media) VALUES (%s, %s, %s, %s, %s, %s, %s)"
                values = (nome, telefone, observacoes, a_atendimento, a_pizzas, a_entregas, media)
                cursor.execute(query, values)
                conn.commit()
                mensagem = "Dados enviados. Obrigado pela sua colaboração!"
                flash(mensagem, 'success')

        except psycopg2.Error as err:
            mensagem = f"Erro ao inserir dados: {err}"
            flash(mensagem, 'error')
            logging.exception(f"Erro de banco de dados ao inserir dados: {err}")
        finally:
            close_db_connection(conn)

    media_geral = calcular_media()
    return render_template('index.html', mensagem=mensagem, media_geral=media_geral)

@app.route('/resultados', methods=['GET', 'POST'])
def resultados():
    error = None
    conn = get_db_connection()

    if not conn:
        return render_template('resultados.html', resultados=[], error="Falha ao conectar ao banco de dados.")

    try:
        with conn.cursor() as cursor:
            query = f"SELECT id, pessoas, numero_telefone, observacoes, a_atendimento, a_pizzas, a_entregas, media FROM {nome_da_tabela}"
            cursor.execute(query)
            resultados = cursor.fetchall()

            if request.method == 'POST':
                ids_para_excluir = request.form.getlist('selecionar')

                if ids_para_excluir:
                    try:
                        # Validate and convert IDs to integers
                        ids_para_excluir = [int(id) for id in ids_para_excluir if id.isdigit()]
                        if not ids_para_excluir:
                            raise ValueError("Nenhum ID válido selecionado.")

                        placeholders = ', '.join(['%s'] * len(ids_para_excluir))
                        query = f"DELETE FROM {nome_da_tabela} WHERE id IN ({placeholders})"
                        cursor.execute(query, ids_para_excluir)
                        conn.commit()
                        flash("Registros excluídos com sucesso!", 'success')
                        return redirect(url_for('resultados'))

                    except (ValueError, psycopg2.Error) as err:
                        logging.error(f"Erro ao excluir dados: {err}")
                        error = f"Erro ao excluir dados: {err}"
                        flash(error, 'error')

                else:
                    error = "Nenhum registro selecionado para exclusão."
                    flash(error, 'warning')

    except psycopg2.Error as err:
        logging.error(f"Erro ao buscar dados: {err}")
        error = f"Erro ao buscar dados: {err}"
        flash(error, 'error')

    finally:
        close_db_connection(conn)

    return render_template('resultados.html', resultados=resultados, error=error)

def calcular_media():
    """Calculates the average 'media' value from the 'banco_teste01' table."""
    conn = get_db_connection()
    if not conn:
        return None

    try:
        with conn.cursor() as cursor:
            query = f"SELECT media FROM {nome_da_tabela} WHERE media IS NOT NULL"
            cursor.execute(query)
            resultados = cursor.fetchall()

        if resultados:
            total = sum(float(resultado[0]) for resultado in resultados)
            media = total / len(resultados)
            return round(media, 2)
        else:
            return 0

    except psycopg2.Error as err:
        logging.error(f"Erro ao calcular a média: {err}")
        return "Erro ao calcular média"

    finally:
        close_db_connection(conn)

if __name__ == '__main__':
    app.run(debug=True)