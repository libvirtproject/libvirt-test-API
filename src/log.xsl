<?xml version='1.0'?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="html" indent="yes" />
<xsl:template match="/">
<html>
  <head>
      <title>Libvirt testing log</title>
      <link rel="stylesheet" href="src/log.css" type="text/css" media="screen" />
      <script language="javascript">
          <![CDATA[
          var xmlDOc;
          var xslDoc;
          var active_result;
          var active_div_id;

          function init(logname) {
              var xmlDoc;
              var xslDoc;

              active_result = "TOTAL";
              expand_last_div();
          }

          function expand_last_div() {
              divs = document.getElementsByTagName('div');
              last_div = divs[divs.length - 1];
              last_div.style.display = "block";
              active_div_id = last_div.attributes['id'].value;
          }

          function on_result_clicked(div_id, result){
              if (result== active_result && active_div_id == div_id)
                  return;

              active_result = result;
              active_div_id = div_id;

              var table = document.getElementById(div_id + "tb");
              var trs = table.childNodes[1].childNodes;

              if (result == "TOTAL") {
                  for (var i = 0; i < trs.length; i++) {
                      trs[i].style.display = "table-row";
                  }

                  return;
              }

              for (var i = 0; i < trs.length; i++) {
                  var cels = trs[i].childNodes;
                  var is_result = false;

                  for (var j = 0; j < cels.length; j++) {
                      if(cels[j].innerHTML == result) {
                          is_result = true;
                          trs[i].style.display = "table-row";
                          break;
                      }
                  }

                  if (!is_result) {
                      trs[i].style.display = "none";
                  }
              }
          }

          function fold_unfold(id) {
              div = document.getElementById(id);

              if (div.style.display == "block") {
                  div.style.display = "none";
              } else {
                  div.style.display = "block";
              }

              /* fold all other divs */
              /*
              divs = document.getElementsByTagName('div');
              for (var i = 0; i < divs.length; i++) {
                  if (divs[i].attributes['id'].value == id) {
                      continue;
                  } else {
                      divs[i].style.display = "none";
                  }
              }
              */
          }
          ]]>
      </script>
  </head>
  <body onload="init()">
    <!--<H1>Libvirt testing report</H1>-->
    <center><img src="icon.png" alt=""/></center>
    <xsl:for-each select="log/testrun">
      <xsl:variable name="div_id" select="@name"/>
      <h2><b><a href="#{$div_id}" onclick="fold_unfold({$div_id})">Testrun <xsl:value-of select="@name"/></a></b></h2>
      <DIV id="{$div_id}" style="display: none;">
        <table border="0" class="statu-list" cellspan="0" cellspacing="0">
          <tr>
            <th><a href="#{$div_id}" onclick="on_result_clicked({$div_id}, 'TOTAL')">Total</a></th>
            <th><a href="#{$div_id}" onclick="on_result_clicked({$div_id}, 'PASS')">PASS</a></th>
            <th><a href="#{$div_id}" onclick="on_result_clicked({$div_id}, 'FAIL')">FAIL</a></th>
            <!--<th><a href="#{$div_id}" onclick="on_result_clicked({$div_id}, 'SKIP')">SKIP</a></th>-->
            <th>Start</th>
            <th>End</th>
          </tr>
          <tr>
            <td><xsl:value-of select="total"/></td>
            <td><xsl:value-of select="pass"/></td>
            <td><xsl:value-of select="fail"/></td>
            <!--<td><xsl:value-of select="skip"/></td>-->
            <td><xsl:value-of select="start_time"/></td>
            <td><xsl:value-of select="end_time"/></td>
          </tr>
        </table>

        <table id="{$div_id}tb" class="list" cellspan="0" cellspacing="0">
          <thead>
            <tr>
              <th width="5%">No.</th>
              <th width="5%">Result</th>
              <th width="10%">Start</th>
              <th width="10%">End</th>
              <th width="65%">Test Procedure</th>
             <!-- <th width="5%">Case Result</th>-->
            </tr>
          </thead>
          <tbody>
            <xsl:for-each select="test">
              <tr>
                <td>
                  <xsl:variable name="link" select="path"/>
                  <a href="{$link}"><xsl:value-of select="@id"/> </a>
                </td>
                <xsl:choose>
                  <xsl:when test="result = 'PASS'">
                    <td class="pass"><xsl:value-of select="result"/></td>
                  </xsl:when>
                  <xsl:when test="result = 'FAIL'">
                    <td class="fail"><xsl:value-of select="result"/></td>
                  </xsl:when>
                  <xsl:otherwise>
                    <td></td>
                  </xsl:otherwise>
                </xsl:choose>
                <td><xsl:value-of select="start_time"/></td>
                <td><xsl:value-of select="end_time"/></td>
                <td>
                  <table class="pro" cellspacing="0" cellspan="0" >
                    <xsl:for-each select="test_procedure">
                      <tr>
                        <td class="li-tit">
                          <xsl:value-of select="action/@name"/>
                        </td>
                        <td>
                          <xsl:for-each select="action/arg">
                            <span>
                              <xsl:value-of select="@name"/>
                              <xsl:text>=</xsl:text>
                              <xsl:value-of select="."/>
                            </span>
                          </xsl:for-each>
                        </td>
                        <td class="result-td">
                        <xsl:for-each select="result">
                           <xsl:if test="self::node()[text()='FAIL']">
                             <tr class="fail"><xsl:value-of select="current()"/></tr>
                           </xsl:if>
                           <xsl:if test="self::node()[text()='PASS']">
                             <tr class="pass"><xsl:value-of select="current()"/></tr>
                           </xsl:if>
                        </xsl:for-each>
                        </td>
                      </tr>
                    </xsl:for-each>
                  </table>
                </td>
              </tr>
            </xsl:for-each>
          </tbody>
        </table>
      </DIV>
    </xsl:for-each>
  </body>
</html>
</xsl:template>
</xsl:stylesheet>
