# BeneficiarFounder
Repository for BIV hackaton  
Usage: 
1. Build docker inside project folder: docker build -t my-solution.
2. Run docker, specifying path to .tsv files:  docker run --rm -v $/path/to/files:/app my-solution.
3. Inside /path/to/files/ folder you will find output.tsv file, which contains list of all beneficiaries of companies in company.tsv file.

