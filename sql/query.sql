Select Distinct
_Part.PartNumber as PartPartNumber,
_Part.Description as PartDescription,
_Part.ExtraDescription
from monitor.Part as _Part
WHERE (_Part.Type IN (0)) AND _Part.Status <> 99 and _Part.PartNumber LIKE '1003___'
Order by PartPartNumber ASC;