for f in bleu-results/*; do
  wc $f
done

for f in bleu-results/*.bleu.txt; do
  echo $f
  cat $f
done
