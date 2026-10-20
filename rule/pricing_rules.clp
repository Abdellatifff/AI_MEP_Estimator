;;
;; Pricing Rules v6 - Components-based
;;

(deftemplate boq_item
   (slot item_description (type STRING))
   (slot size (type STRING))
   (slot connection (type STRING))
   (slot action_code (type STRING))
   (slot quantity (type FLOAT))
   (slot include_tax (type STRING) (default "no")))

(deftemplate price_row
   (slot table_name (type STRING))
   (slot size (type STRING))
   (slot component (type STRING))
   (slot price (type FLOAT)))

(deftemplate selected_table
   (slot table_name (type STRING)))

(deftemplate pricing_result
   (slot item_description (type STRING))
   (slot size (type STRING))
   (slot connection (type STRING))
   (slot action_code (type STRING))
   (slot quantity (type FLOAT))
   (slot table_name (type STRING))
   (slot unit_price (type FLOAT))
   (slot subtotal (type FLOAT))
   (slot tax_amount (type FLOAT))
   (slot discount_amount (type FLOAT))
   (slot grand_total (type FLOAT))
   (slot breakdown (type STRING)))

(deftemplate error_result
   (slot message (type STRING)))

(deffunction component-included (?comp ?code)
   (if (eq ?comp "supply_price") then
       (return (> (str-index "S" ?code) 0)))
   (if (eq ?comp "installation_price") then
       (return (> (str-index "I" ?code) 0)))
   (if (eq ?comp "welding_or_grooving") then
       (return (> (str-index "W" ?code) 0)))
   (if (eq ?comp "painting_price") then
       (return (> (str-index "P" ?code) 0)))
   (if (eq ?comp "supports_and_hangers") then
       (return (> (str-index "H" ?code) 0)))
   (if (eq ?comp "testing_and_commissioning") then
       (return (> (str-index "T" ?code) 0)))
   (return FALSE))

(defrule select_table
   (declare (salience 100))
   (boq_item (connection ?conn))
   =>
   (assert (selected_table (table_name ?conn))))

(defrule error_no_rule
   (declare (salience 5))
   (boq_item (connection ?conn))
   (not (selected_table))
   =>
   (assert (error_result
      (message (str-cat "لا يوجد جدول للـ connection: " ?conn)))))

(defrule error_no_price
   (declare (salience 40))
   (boq_item (size ?size))
   (selected_table (table_name ?tbl))
   (not (price_row (table_name ?tbl) (size ?size)))
   =>
   (assert (error_result
      (message (str-cat "لا توجد أسعار للقطر " ?size " في " ?tbl)))))

(defrule calculate_pricing
   (declare (salience 30))
   (boq_item (item_description ?desc) (size ?size) (connection ?conn)
             (action_code ?code) (quantity ?q) (include_tax ?tax_flag))
   (selected_table (table_name ?tbl))
   (price_row (table_name ?tbl) (size ?size))
   (not (error_result))
   (not (pricing_result))
   =>
   (bind ?unit 0.0)
   (bind ?bd "")
   (do-for-all-facts ((?pr price_row))
      (and (eq ?pr:table_name ?tbl) (eq ?pr:size ?size))
      (if (component-included ?pr:component ?code) then
          (bind ?unit (+ ?unit ?pr:price))
          (bind ?bd (str-cat ?bd ?pr:component "=" ?pr:price " "))))

   (bind ?subtotal (* ?unit ?q))

   (bind ?tax 0.0)
   (if (eq ?tax_flag "yes") then
      (bind ?tax (* ?subtotal 0.14)))

   (bind ?before_discount (+ ?subtotal ?tax))

   (bind ?discount 0.0)
   (if (> ?q 100) then
      (bind ?discount (* ?before_discount 0.05)))

   (bind ?grand (- ?before_discount ?discount))

   (assert (pricing_result
      (item_description ?desc)
      (size ?size)
      (connection ?conn)
      (action_code ?code)
      (quantity ?q)
      (table_name ?tbl)
      (unit_price ?unit)
      (subtotal ?subtotal)
      (tax_amount ?tax)
      (discount_amount ?discount)
      (grand_total ?grand)
      (breakdown ?bd))))