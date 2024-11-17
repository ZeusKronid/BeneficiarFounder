FROM continuumio/miniconda3:latest

WORKDIR /

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

RUN conda install --channel conda-forge pygraphviz

CMD ["python", "run.py"]
