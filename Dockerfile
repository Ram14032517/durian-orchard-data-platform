FROM python:3.12-slim
WORKDIR /app
COPY tools/requirements-cloud.txt tools/requirements-cloud.txt
RUN pip install --no-cache-dir -r tools/requirements-cloud.txt
COPY tools/serve_orchard_cloud.py tools/serve_orchard_analysis.py tools/orchard_current_context.py tools/supabase_orchard.py tools/clean_stale_weather.py tools/train_monthly_production.py tools/compare_harvest_stage_yield.py tools/analyze_harvest_backcast.py tools/
COPY tools/durian_model/common.py tools/durian_model/common.py
COPY ml/orchard_live_model.py ml/orchard_live_model.py
COPY models/orchard_soil_6h.json models/orchard_soil_6h.json
COPY research_data/five_province_history/ research_data/five_province_history/
COPY research_data/priority_provinces/soil_layers/ research_data/priority_provinces/soil_layers/
RUN useradd --create-home orchard && chown -R orchard:orchard /app
USER orchard
ENV PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1
CMD ["sh", "-c", "exec gunicorn --chdir tools --bind 0.0.0.0:${PORT:-10000} --workers 1 --threads 4 --timeout 120 'serve_orchard_cloud:create_app()'"]
