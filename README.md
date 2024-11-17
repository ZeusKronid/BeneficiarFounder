# BeneficiarFounder
Repository for BIV hackaton  
Usage: 
1. Build docker inside project folder: docker build -t my-solution .
2. Run docker, specifying path to .tsv files:  docker run --rm -v $/path/to/files:/app my-solution.
3. Inside /path/to/files/ folder you will find output.tsv file, which contains list of all beneficiaries of companies in company.tsv file.

Репозиторий создан для BIV хакатона    
Использование: 
1. Соберите докер, находясь внутри папки проекта командой: docker build -t my-solution .  
2. Запустите докер, указав путь к папке с .tsv файлами командой:  docker run --rm -v ${/path/to/files}:/app my-solution
3. Внутри {/path/to/files} папки появится файл output.tsv, содержащий список бенефициаров компаний. 

Альтернативный способ: 
tar файл с упакованным контейнером можно найти по ссылке: 
1. Загрузите модель: docker load < beneficiar_founder.tar
2. Запустите докер, указав путь к папке с .tsv файлами командой: docker run --rm -v $/path/to/files:/app my-solution.
3. Внутри {/path/to/files} папки появистя файл output.tsv, содержащий список бенефициаров компаний. 
