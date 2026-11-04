# Orquestador del pipeline de referencias

## Objetivo y alcance

El esquema proporciona 8 preguntas de calidad y 8 de RD. La lateralidad
(Calidad/2) se toma de los metadatos de carga de la imagen, sin LLM: no la
reescribas desde el informe ni la delegues a un modelo.

Las otras 15 preguntas salen exclusivamente del informe por ojo, con respuestas
breves y citas exactas. No interpretamos imágenes ni completamos esas respuestas
con etiquetas, predicciones o metadatos. Null documental no es ausencia clínica.

El chat coordina extractor y revisor por categoría. El helper local no llama
modelos: prepara mensajes y valida tipos/cobertura/citas/offsets.
Las decisiones semánticas siguen requiriendo el informe, la pregunta y las reglas.
No puede garantizarse ausencia de errores solo mediante instrucciones.

## Adjudicación

Tras la revisión, evaluá las propuestas con la lista semántica siguiente y
guardá un JSON de decisiones por los IDs aún pendientes, con esta forma:

   `{"1":{"verdict":"approve","note":"La cita declara mala calidad y aplica la regla."},"2":{"verdict":"needs_review","note":"La respuesta afirma un vaso venoso no especificado."}}`

Usá los IDs reales, todos exactamente una vez. Cada nota debe decir qué
información concreta justifica el veredicto; no copies frases genéricas de éxito.
No apruebes solo por accept/correct del revisor. El helper vuelve a comprobar
propuesta, contrato, citas y algunos invariantes explícitos y calcula offsets.
No puede aprobar si falla un control mecánico, aunque tu veredicto diga approve.
Escalate queda needs_review.

## Lista semántica para cada propuesta

Primero identificá a qué pregunta responde; luego evaluá únicamente su evidencia:
- Lesiones específicas: silencio/negación general de RD no prueba ausencia de
  exudados, hemorragias, venas, IRMA, etc. Sin información específica: null/[] válido.
- Calidad: mala/insuficiente calidad o no informabilidad explícitas → no informable;
  suficiente/informable explícitas → afirmativa. Media/defecto aislado → null para
  informabilidad. Mala calidad no elimina otras lesiones documentadas.
- Evidencia: conserva afirmación, negación y calificadores. "foco" solo no prueba
  defecto; "falla en la iluminación y foco" sí. No reconstruir puntuación ni citas.
- Incertidumbre: answer conserva compatibles/sospecha/posible del informe; la cita
  incierta no respalda una respuesta confirmatoria. No desambiguar expresiones
  conjuntas microhemorragias/microaneurismas.
- Hemorragias incluye microhemorragias; microaneurismas solos no implican hemorragias.
- Tortuosidad vascular sin contexto venoso explícito no responde sobre venas.
- Morfología sola no responde calidad de visualización. Visualización explícita
  permite respuesta parcial sin extender a otras estructuras. Visibilidad parcial
  de mácula no responde su condición clínica/maculopatía.
- Respuestas parciales contienen solo lo respaldado, sin completar negativos ni
  añadir "no se informa sobre el contraste" ni explicaciones sobre partes ausentes. No exigir todas las partes para aceptar una parcial.
- Contradicción no resoluble → needs_review; falta de evidencia → null aprobado.
- corrected idéntico al candidato incumple el contrato, no es corrección válida.
