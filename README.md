# BeneficiarFounder
Repository for BIV hackaton  
Usage: 
1. Create docker inside project folder container docker build -t my-solution .
2. Run, specifying path to .tsv files  docker run --rm -v $/path/to/files:/app my-solution
3. Inside /path/to/files/ folder you will find output.tsv file, which contains list of all beneficiars of companies in company.tsv file

